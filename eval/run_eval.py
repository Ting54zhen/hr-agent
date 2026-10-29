"""检索评测：Recall@K + MRR。

只评测带 expected_sources 的 policy/mixed 问题，不需要 LLM Key。
用法：
    python eval/run_eval.py
    python eval/run_eval.py --top-k 5 --output D:/ClaudeCode/数据/hr-agent-检索评测结果.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.retriever import get_retriever  # noqa: E402


def load_items(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def evaluate(items: list[dict[str, Any]], top_k: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    retriever = get_retriever()
    if not retriever.chunks:
        raise SystemExit("chunks 为空：请先运行 python -m app.rag.ingest")

    details: list[dict[str, Any]] = []
    hits = 0
    rr_total = 0.0
    evaluated = 0

    for item in items:
        expected = item.get("expected_sources") or []
        if not expected:
            continue
        evaluated += 1
        chunks = retriever.search(item["question"], top_k=top_k)
        sources = [chunk.source for chunk in chunks]
        first_rank = None
        for rank, source in enumerate(sources, start=1):
            if source in expected:
                first_rank = rank
                break
        hit = first_rank is not None
        hits += int(hit)
        rr_total += (1.0 / first_rank) if first_rank else 0.0

        details.append(
            {
                "id": item["id"],
                "question": item["question"],
                "expected_sources": expected,
                "hit": hit,
                "first_rank": first_rank,
                "retrieved": [
                    {
                        "source": chunk.source,
                        "heading": chunk.heading,
                        "score": chunk.score,
                        "rerank_score": chunk.rerank_score,
                    }
                    for chunk in chunks
                ],
            }
        )

    summary = {
        "evaluated": evaluated,
        "recall_at_k": round(hits / evaluated, 4) if evaluated else 0.0,
        "mrr": round(rr_total / evaluated, 4) if evaluated else 0.0,
        "top_k": top_k,
        "total_items": len(items),
    }
    return summary, details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa", type=Path, default=PROJECT_ROOT / "eval" / "qa.jsonl")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    items = load_items(args.qa)
    summary, details = evaluate(items, args.top_k)

    print("=" * 72)
    for item in details:
        mark = "HIT " if item["hit"] else "MISS"
        rank = item["first_rank"] if item["first_rank"] is not None else "-"
        top = item["retrieved"][0] if item["retrieved"] else None
        top_text = f"{top['source']} ({top['score']:.4f})" if top else "无召回"
        print(f"[{item['id']}] {mark} rank={rank}  {item['question']}")
        print(f"      top1: {top_text}")
    print("=" * 72)
    print(
        f"Recall@{summary['top_k']} = {summary['recall_at_k']:.2%}  "
        f"MRR = {summary['mrr']:.4f}  "
        f"({summary['evaluated']}/{summary['total_items']} 条参与检索评测)"
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": summary, "details": details}
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"结果已写入：{args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
