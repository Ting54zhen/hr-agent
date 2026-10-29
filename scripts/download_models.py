"""下载 HR Agent 需要的本地模型到 HF 缓存。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import snapshot_download

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
os.environ.setdefault("HF_HOME", "D:/Dev/cache/huggingface")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

MODELS = ["BAAI/bge-m3", "BAAI/bge-reranker-v2-m3"]

# 只下 dense 检索/重排需要的文件，跳过 onnx、pytorch_model.bin 等重复产物。
ALLOW_PATTERNS = [
    "*.json",
    "*.txt",
    "*.model",
    "*.safetensors",
    "*.bin",
    "*.py",
    "sentencepiece*",
    "tokenizer*",
    "1_Pooling/*",
    "modules.json",
]


def main() -> None:
    print(f"HF_HOME={os.getenv('HF_HOME')}", flush=True)
    print(f"HF_ENDPOINT={os.getenv('HF_ENDPOINT')}", flush=True)
    for repo_id in MODELS:
        print(f"==> downloading {repo_id}", flush=True)
        path = snapshot_download(
            repo_id=repo_id,
            allow_patterns=ALLOW_PATTERNS,
            max_workers=4,
        )
        print(f"OK {repo_id} -> {path}", flush=True)


if __name__ == "__main__":
    main()
