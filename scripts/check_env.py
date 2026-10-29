"""检查 HR Agent 本地环境是否就绪。"""

from __future__ import annotations

import importlib.metadata as md
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
os.environ.setdefault("HF_HOME", "D:/Dev/cache/huggingface")


PACKAGES = [
    "langchain",
    "langgraph",
    "langchain-mcp-adapters",
    "mcp",
    "chromadb",
    "sentence-transformers",
    "FlagEmbedding",
    "torch",
    "fastapi",
    "pymysql",
    "redis",
    "pymupdf",
]


def check_packages() -> None:
    print("== Python 包 ==")
    for name in PACKAGES:
        try:
            print(f"  {name}: {md.version(name)}")
        except md.PackageNotFoundError:
            print(f"  {name}: MISSING")


def check_torch() -> None:
    print("== PyTorch ==")
    try:
        import torch

        print(f"  version: {torch.__version__}")
        print(f"  cuda available: {torch.cuda.is_available()}")
    except Exception as exc:  # noqa: BLE001
        print(f"  torch import failed: {exc}")


def check_mysql() -> None:
    print("== MySQL ==")
    try:
        import pymysql

        conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "hr"),
            password=os.getenv("MYSQL_PASSWORD", "hr"),
            database=os.getenv("MYSQL_DATABASE", "hr"),
            connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM employees")
            employees = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM leave_balances")
            balances = cur.fetchone()[0]
        conn.close()
        print(f"  employees: {employees}, leave_balances: {balances}")
    except Exception as exc:  # noqa: BLE001
        print(f"  MySQL check failed: {exc}")


def check_redis() -> None:
    print("== Redis ==")
    try:
        import redis

        client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
        print(f"  ping: {client.ping()}")
        modules = [item.get("name") for item in client.module_list()]
        print(f"  modules: {modules}")
    except Exception as exc:  # noqa: BLE001
        print(f"  Redis check failed: {exc}")


def check_models() -> None:
    print("== 模型 ==")
    hf_home = Path(os.getenv("HF_HOME", "D:/Dev/cache/huggingface"))
    models = [
        ("embed", os.getenv("EMBED_MODEL", "D:/Dev/models/bge-m3")),
        ("reranker", os.getenv("RERANK_MODEL", "D:/Dev/models/bge-reranker-v2-m3")),
    ]
    for label, model in models:
        local = Path(model)
        if local.is_dir():
            weights = (
                list(local.glob("*.safetensors"))
                + list(local.glob("*.bin"))
                + list(local.glob("pytorch_model*.bin"))
            )
            size = max((p.stat().st_size for p in weights), default=0)
            if size > 1_500_000_000:
                status = f"OK ({size / 1024 / 1024 / 1024:.2f} GB)"
            elif size:
                status = f"PARTIAL ({size / 1024 / 1024:.0f} MB)"
            else:
                status = "MISSING WEIGHTS"
            print(f"  {label}: {status} ({local})")
            continue
        cache = hf_home / "hub" / ("models--" + model.replace("/", "--"))
        print(f"  {label}: {'OK' if cache.exists() else 'NOT DOWNLOADED'} ({cache})")


def main() -> int:
    print(f"Python: {sys.version}")
    print(f"Executable: {sys.executable}")
    check_packages()
    check_torch()
    check_mysql()
    check_redis()
    check_models()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
