"""离线冒烟测试：MCP 三工具 + RAG 检索。不需要 LLM Key。

用法：
    python scripts/smoke_test.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.agent.tools import load_hr_tools  # noqa: E402
from app.rag.retriever import get_retriever  # noqa: E402


def _payload(result):
    if isinstance(result, list) and result:
        return result[0].get("text", "")
    return str(result)


async def check_mcp() -> bool:
    print("== MCP 工具 ==")
    tools = await load_hr_tools()
    by_name = {tool.name: tool for tool in tools}
    expected = {
        "get_leave_balance",
        "get_attendance",
        "get_org_info",
        "get_employee_profile",
    }
    missing = expected - set(by_name)
    if missing:
        print(f"  缺少工具：{sorted(missing)}")
        return False

    checks = [
        ("get_leave_balance", {"employee_id": 1001}, '"annual_remaining": 7'),
        ("get_attendance", {"employee_id": 1001, "month": "2026-10"}, '"late": 1'),
        ("get_employee_profile", {"employee_id": 1001}, '"department": "研发部"'),
        ("get_org_info", {"name": "张三"}, '"department": "研发部"'),
        ("get_leave_balance", {"employee_id": 9999}, '"ok": false'),
    ]
    ok = True
    for name, args, expected_text in checks:
        text = json.dumps(
            json.loads(_payload(await by_name[name].ainvoke(args))),
            ensure_ascii=False,
        )
        passed = expected_text in text
        ok = ok and passed
        print(f"  {'PASS' if passed else 'FAIL'} {name} {args}")
    return ok


def check_retrieval() -> bool:
    print("== RAG 检索 ==")
    retriever = get_retriever()
    if not retriever.chunks:
        print("  FAIL 没有 chunk，请先运行 python -m app.rag.ingest")
        return False

    query = "年假没休完可以结转到什么时候？"
    results = retriever.search(query, top_k=3)
    if not results:
        print("  FAIL 没有召回结果")
        return False
    for index, item in enumerate(results, start=1):
        score = item.rerank_score if item.rerank_score is not None else item.score
        print(f"  {index}. {item.source} / {item.heading}  score={score:.4f}")
    hit = any(item.source == "示例-假期管理制度.md" for item in results)
    print(f"  {'PASS' if hit else 'FAIL'} 命中示例-假期管理制度.md")
    return hit


async def main() -> int:
    mcp_ok = await check_mcp()
    rag_ok = check_retrieval()
    return 0 if (mcp_ok and rag_ok) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
