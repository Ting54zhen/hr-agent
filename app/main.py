"""FastAPI 入口：SSE 流式对话 + Redis 会话持久化。"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.agent.graph import build_graph
from app.agent.tools import load_hr_tools
from app.auth import AuthStorageError, authenticate, create_access_token, require_user
from app.config import settings
from app.rag.retriever import get_retriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("hr-agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.graph = None
    app.state.tools = []
    app.state.retriever = None
    app.state.startup_error = None
    app.state.checkpointer_kind = "none"
    stack = AsyncExitStack()

    if settings.hr_auth_secret == "dev-only-change-me":
        logger.warning("HR_AUTH_SECRET 仍为默认值，仅适合本地演示")

    try:
        try:
            app.state.retriever = await asyncio.to_thread(get_retriever)
        except Exception as exc:  # noqa: BLE001
            logger.exception("初始化检索器失败")
            app.state.startup_error = f"retriever: {exc}"

        try:
            app.state.tools = await load_hr_tools()
        except Exception as exc:  # noqa: BLE001
            logger.exception("加载 MCP 工具失败，Agent 将退化为纯 RAG")
            app.state.startup_error = f"mcp: {exc}"

        try:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver

            checkpointer = await stack.enter_async_context(
                AsyncRedisSaver.from_conn_string(settings.redis_url)
            )
            await checkpointer.asetup()
            app.state.checkpointer_kind = "redis"
        except Exception:  # noqa: BLE001
            logger.exception("Redis checkpointer 初始化失败，降级为 MemorySaver")
            await stack.aclose()
            stack = AsyncExitStack()
            from langgraph.checkpoint.memory import MemorySaver

            checkpointer = MemorySaver()
            app.state.checkpointer_kind = "memory"

        try:
            app.state.graph = build_graph(app.state.tools, checkpointer)
        except Exception as exc:  # noqa: BLE001
            logger.exception("构建 Agent 图失败")
            app.state.startup_error = f"graph: {exc}"

        yield
    finally:
        await stack.aclose()


app = FastAPI(
    title="HR 知识库智能问答 Agent",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if WEB_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(WEB_DIR), html=True), name="ui")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(default="demo", max_length=100)


class LoginRequest(BaseModel):
    employee_id: int = Field(ge=1)
    password: str = Field(min_length=1, max_length=128)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "".join(parts)
    return ""


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "name": "HR 知识库智能问答 Agent",
        "ui": "/ui/",
        "docs": "/docs",
        "health": "/health",
        "login": "/auth/login",
    }


@app.get("/health")
async def health(request: Request) -> dict[str, Any]:
    retriever = getattr(request.app.state, "retriever", None)
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_configured": settings.llm_configured,
        "graph_ready": getattr(request.app.state, "graph", None) is not None,
        "checkpointer": getattr(request.app.state, "checkpointer_kind", "none"),
        "chunks": len(retriever.chunks) if retriever is not None else 0,
        "tools": [tool.name for tool in getattr(request.app.state, "tools", [])],
        "startup_error": getattr(request.app.state, "startup_error", None),
    }


@app.post("/auth/login")
async def login(payload: LoginRequest) -> dict[str, Any]:
    try:
        user = await asyncio.to_thread(authenticate, payload.employee_id, payload.password)
    except AuthStorageError:
        raise HTTPException(
            status_code=503, detail="登录服务暂不可用，请检查 MySQL 连接"
        ) from None

    if user is None:
        raise HTTPException(status_code=401, detail="工号或密码不正确")

    token = create_access_token(
        employee_id=user["employee_id"],
        name=user["name"],
        department=user["department"],
        email=user.get("email", ""),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.hr_auth_token_ttl_hours * 3600,
        "user": user,
    }


@app.get("/auth/me")
async def me(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return {
        "employee_id": int(user["sub"]),
        "name": user.get("name", ""),
        "department": user.get("department", ""),
        "email": user.get("email", ""),
    }


@app.post("/search")
async def search(payload: SearchRequest, request: Request) -> dict[str, Any]:
    retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        raise HTTPException(status_code=503, detail="检索器未初始化，请先运行文档入库")
    results = await asyncio.to_thread(retriever.search, payload.query, payload.top_k)
    return {
        "query": payload.query,
        "confident": retriever.is_confident(results),
        "results": [
            {
                "source": item.source,
                "heading": item.heading,
                "score": item.score,
                "rerank_score": item.rerank_score,
                "content": item.content,
            }
            for item in results
        ],
    }


@app.post("/chat")
async def chat(
    payload: ChatRequest,
    request: Request,
    user: dict[str, Any] = Depends(require_user),
) -> StreamingResponse:
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Agent 未就绪，请检查 LLM Key、Redis、MCP 和文档入库。"
                f" 原因：{getattr(request.app.state, 'startup_error', 'unknown')}"
            ),
        )

    employee_id = int(user["sub"])
    if employee_id not in settings.allowed_ids:
        raise HTTPException(status_code=403, detail="该工号没有查询权限")

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message 不能为空")

    session_id = payload.session_id.strip() or "demo"
    config = {"configurable": {"thread_id": session_id}}
    inputs = {
        "messages": [HumanMessage(content=message)],
        "employee_id": employee_id,
        "route": "",
        "context": "",
        "sources": [],
        "retry_count": 0,
        "grounded": False,
        "check_reason": "",
    }

    async def event_stream():
        generate_runs = 0
        try:
            yield _sse("meta", {"session_id": session_id, "employee_id": employee_id})
            async for event in graph.astream_events(inputs, config=config, version="v2"):
                kind = event.get("event")
                metadata = event.get("metadata", {}) or {}
                node = metadata.get("langgraph_node")

                # 条件边（如 route_after_generate）也会带 langgraph_node=generate，
                # 这里只统计 generate 节点本身的启动事件，避免误发 reset。
                if (
                    kind == "on_chain_start"
                    and node == "generate"
                    and event.get("name") == "generate"
                ):
                    generate_runs += 1
                    if generate_runs > 1:
                        yield _sse("reset", {"reason": "事实校验未通过，重新生成"})

                if kind == "on_chat_model_stream" and node == "generate":
                    text = _chunk_text(event.get("data", {}).get("chunk"))
                    if text:
                        yield _sse("token", {"text": text})

            snapshot = await graph.aget_state(config)
            values = snapshot.values or {}
            messages = values.get("messages", [])
            answer = ""
            for message in reversed(messages):
                if getattr(message, "type", "") == "ai" and not getattr(
                    message, "tool_calls", None
                ):
                    answer = _chunk_text(message)
                    break

            yield _sse(
                "done",
                {
                    "answer": answer,
                    "route": values.get("route"),
                    "grounded": values.get("grounded"),
                    "check_reason": values.get("check_reason"),
                    "retry_count": values.get("retry_count", 0),
                    "sources": values.get("sources", []),
                },
            )
        except Exception:  # noqa: BLE001
            logger.exception("对话失败")
            yield _sse("error", {"message": "对话失败，请查看服务端日志后重试"})


    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
