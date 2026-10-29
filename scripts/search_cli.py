"""命令行测试 /search（只走检索，不调用大模型）。

用法：
    python scripts/search_cli.py "年假没休完可以结转到什么时候"
    python scripts/search_cli.py "迟到30分钟以内怎么处理" --top-k 5
"""

from __future__ import annotations

import argparse
import sys

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description="测试 HR Agent 的 /search 接口")
    parser.add_argument("query", help="检索问题")
    parser.add_argument("--top-k", type=int, default=3, help="返回条数，1-20")
    parser.add_argument("--url", default="http://127.0.0.1:8000/search")
    args = parser.parse_args()

    try:
        response = requests.post(
            args.url,
            json={"query": args.query, "top_k": args.top_k},
            timeout=300,
        )
    except requests.RequestException as exc:
        print(f"连不上服务：{exc}", file=sys.stderr)
        print("先在另一个终端运行：python -m app.main", file=sys.stderr)
        return 1

    print(f"HTTP {response.status_code}")
    if response.status_code != 200:
        print(response.text, file=sys.stderr)
        return 1

    results = response.json().get("results", [])
    for index, item in enumerate(results, start=1):
        score = item.get("score", 0.0)
        print(
            f"{index}. score={score:.4f}  "
            f"{item.get('source', '')} | {item.get('heading', '')}"
        )
    if not results:
        print("没有检索到内容：请先运行 python -m app.rag.ingest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
