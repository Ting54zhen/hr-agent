"""LangGraph 状态机。

路由 → (知识库检索) → (MCP 工具调用) → 生成 → 事实校验 → 必要时重试/兜底
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.agent.prompts import (
    AGENT_SYSTEM,
    CHECK_PROMPT,
    GENERATE_PROMPT,
    ROUTER_SYSTEM,
    CheckDecision,
    RouteDecision,
)
from app.config import settings
from app.rag.retriever import get_retriever

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    employee_id: int
    route: str
    context: str
    sources: list[dict[str, Any]]
    retry_count: int
    grounded: bool
    check_reason: str


def make_llm():
    if not settings.llm_configured:
        raise RuntimeError(
            "LLM 未配置：请在 .env 中填写 OPENAI_API_KEY（或 ANTHROPIC_API_KEY）后重启。"
        )

    if settings.llm_provider.lower() == "anthropic":
        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0.1,
            timeout=60,
            max_retries=2,
        )

    kwargs: dict[str, Any] = {
        "model": settings.llm_model,
        "api_key": settings.openai_api_key,
        "temperature": 0.1,
        "timeout": 60,
        "max_retries": 2,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


def _message_text(message: AnyMessage) -> str:
    content = getattr(message, "content", "")
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
    return str(content)


def _last_user_text(messages: list[AnyMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return _message_text(message)
    return ""


def _last_ai_text(messages: list[AnyMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not getattr(message, "tool_calls", None):
            return _message_text(message)
    return ""


def _last_user_index(messages: list[AnyMessage]) -> int:
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return index
    return -1


def _history_before_last_user(messages: list[AnyMessage]) -> list[AnyMessage]:
    index = _last_user_index(messages)
    if index <= 0:
        return []
    history: list[AnyMessage] = []
    for message in messages[:index]:
        if isinstance(message, HumanMessage):
            history.append(message)
        elif isinstance(message, AIMessage) and not getattr(message, "tool_calls", None):
            history.append(message)
    return history


def _tool_results_after_last_user(messages: list[AnyMessage]) -> str:
    index = _last_user_index(messages)
    results = [
        _message_text(message)
        for message in messages[index + 1 :]
        if isinstance(message, ToolMessage)
    ]
    return "\n\n".join(results)


def build_graph(tools: list[BaseTool] | None = None, checkpointer=None):
    tools = tools or []
    llm = make_llm()
    router_llm = llm.with_structured_output(RouteDecision)
    checker_llm = llm.with_structured_output(CheckDecision)
    llm_with_tools = llm.bind_tools(tools) if tools else llm
    tool_node = ToolNode(tools) if tools else None

    async def router_node(state: AgentState) -> dict[str, Any]:
        question = _last_user_text(state["messages"])
        employee_id = state.get("employee_id", "")
        try:
            decision = await router_llm.ainvoke(
                [
                    SystemMessage(content=ROUTER_SYSTEM),
                    HumanMessage(
                        content=f"当前登录员工工号：{employee_id}\n用户问题：{question}"
                    ),
                ]
            )
            route = decision.route
            if route not in {"policy", "data", "mixed", "chitchat"}:
                route = "mixed"
            logger.info("router -> %s (%s)", route, decision.reason)
            return {"route": route}
        except Exception:  # noqa: BLE001
            logger.exception("路由失败，降级为 mixed")
            return {"route": "mixed"}

    async def retrieve_node(state: AgentState) -> dict[str, Any]:
        question = _last_user_text(state["messages"])
        try:
            retriever = await asyncio.to_thread(get_retriever)
            results = await asyncio.to_thread(retriever.search, question, 5)
            context = retriever.format_context(results)
            sources = [
                {
                    "source": item.source,
                    "heading": item.heading,
                    "score": item.rerank_score
                    if item.rerank_score is not None
                    else item.score,
                }
                for item in results
            ]
            logger.info("retrieve -> %d chunks", len(results))
            return {"context": context, "sources": sources}
        except Exception:  # noqa: BLE001
            logger.exception("检索失败，继续无资料生成")
            return {"context": "", "sources": []}

    async def agent_node(state: AgentState) -> dict[str, Any]:
        system = AGENT_SYSTEM.format(
            employee_id=state.get("employee_id", ""),
            context=state.get("context") or "（无）",
        )
        response = await llm_with_tools.ainvoke(
            [SystemMessage(content=system)] + list(state["messages"])
        )
        return {"messages": [response]}

    def should_call_tools(state: AgentState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return "generate"

    async def generate_node(state: AgentState) -> dict[str, Any]:
        messages = list(state["messages"])
        question = _last_user_text(messages)
        history = _history_before_last_user(messages)
        tool_results = _tool_results_after_last_user(messages)
        context = state.get("context") or "（无）"

        if state.get("retry_count", 0) > 0:
            context += (
                "\n\n【重要】上一次回答没有通过事实校验。"
                "请只使用资料和工具结果中明确出现的信息；不足时直接说明无法确认。"
            )

        prompt = GENERATE_PROMPT.invoke(
            {
                "history": history,
                "context": context,
                "tool_results": tool_results or "（无）",
                "question": question,
            }
        )
        response = await llm.ainvoke(prompt)
        if state.get("route") == "chitchat":
            return {
                "messages": [response],
                "grounded": True,
                "check_reason": "chitchat 跳过事实校验",
            }
        return {"messages": [response]}

    async def check_node(state: AgentState) -> dict[str, Any]:
        if state.get("route") == "chitchat":
            return {"grounded": True, "check_reason": "chitchat 跳过事实校验"}

        messages = list(state["messages"])
        question = _last_user_text(messages)
        answer = _last_ai_text(messages)
        context = state.get("context") or "（无）"
        tool_results = _tool_results_after_last_user(messages) or "（无）"

        try:
            decision = await checker_llm.ainvoke(
                CHECK_PROMPT.invoke(
                    {
                        "question": question,
                        "context": context,
                        "tool_results": tool_results,
                        "answer": answer,
                    }
                )
            )
            grounded = bool(decision.grounded)
            reason = decision.reason
        except Exception:  # noqa: BLE001
            logger.exception("事实校验失败，本次放行")
            grounded = True
            reason = "checker_failed"

        retry_count = state.get("retry_count", 0)
        if not grounded:
            retry_count += 1

        logger.info("check -> grounded=%s retry=%d (%s)", grounded, retry_count, reason)
        return {
            "grounded": grounded,
            "check_reason": reason,
            "retry_count": retry_count,
        }

    def route_after_router(state: AgentState) -> str:
        route = state.get("route", "mixed")
        if route == "policy":
            return "retrieve"
        if route == "data":
            return "agent" if tool_node is not None else "generate"
        if route == "mixed":
            return "retrieve"
        return "generate"

    def route_after_retrieve(state: AgentState) -> str:
        if state.get("route") == "mixed" and tool_node is not None:
            return "agent"
        return "generate"

    def route_after_generate(state: AgentState) -> str:
        if state.get("route") == "chitchat":
            return END
        return "check"

    def route_after_check(state: AgentState) -> str:
        if state.get("grounded"):
            return END
        if state.get("retry_count", 0) <= 1:
            return "generate"
        return "fallback"

    async def fallback_node(state: AgentState) -> dict[str, Any]:
        answer = (
            "根据现有资料无法确认这个问题的准确答案。"
            "建议联系 HR 同事核实，或补充更具体的信息后再问我。"
        )
        return {"messages": [AIMessage(content=answer)]}

    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("agent", agent_node)
    graph.add_node("generate", generate_node)
    graph.add_node("check", check_node)
    graph.add_node("fallback", fallback_node)
    if tool_node is not None:
        graph.add_node("tools", tool_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {"retrieve": "retrieve", "agent": "agent", "generate": "generate"},
    )
    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {"agent": "agent", "generate": "generate"},
    )
    graph.add_conditional_edges(
        "agent",
        should_call_tools,
        {"tools": "tools", "generate": "generate"}
        if tool_node is not None
        else {"generate": "generate"},
    )
    if tool_node is not None:
        graph.add_edge("tools", "agent")

    graph.add_conditional_edges(
        "generate",
        route_after_generate,
        {"check": "check", END: END},
    )
    graph.add_conditional_edges(
        "check",
        route_after_check,
        {"generate": "generate", "fallback": "fallback", END: END},
    )
    graph.add_edge("fallback", END)

    return graph.compile(checkpointer=checkpointer)
