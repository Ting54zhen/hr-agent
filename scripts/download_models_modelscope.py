"""从 ModelScope（魔搭）下载 BGE 模型到 D 盘。

国内网络下 ModelScope 通常比 HF 镜像稳定，且不需要处理 Xet。

用法：
    python scripts/download_models_modelscope.py
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

ROOT = Path("D:/Dev/models")

MODELS = {
    "bge-m3": {
        "url": "https://modelscope.cn/models/BAAI/bge-m3/resolve/master",
        "files": [
            "config.json",
            "config_sentence_transformers.json",
            "modules.json",
            "sentence_bert_config.json",
            "pytorch_model.bin",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "sentencepiece.bpe.model",
            "1_Pooling/config.json",
        ],
    },
    "bge-reranker-v2-m3": {
        "url": "https://modelscope.cn/models/BAAI/bge-reranker-v2-m3/resolve/master",
        "files": [
            "config.json",
            "model.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "sentencepiece.bpe.model",
        ],
    },
}


def download_file(url: str, dest: Path, retries: int = 3) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "hr-agent-model-downloader/0.1"}

    for attempt in range(1, retries + 1):
        existing = dest.stat().st_size if dest.exists() else 0
        request_headers = dict(headers)
        if existing:
            request_headers["Range"] = f"bytes={existing}-"

        try:
            with requests.get(
                url,
                headers=request_headers,
                stream=True,
                timeout=(30, 300),
                allow_redirects=True,
            ) as response:
                if response.status_code == 416:
                    print(f"    already complete: {dest.name} ({existing:,} bytes)", flush=True)
                    return
                if response.status_code not in (200, 206):
                    response.raise_for_status()

                append = existing > 0 and response.status_code == 206
                mode = "ab" if append else "wb"
                total = existing if append else 0
                total += int(response.headers.get("Content-Length", "0") or 0)
                written = existing if append else 0
                last_report = time.time()

                with dest.open(mode) as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        written += len(chunk)
                        now = time.time()
                        if now - last_report >= 5:
                            if total:
                                percent = written / total * 100
                                print(
                                    f"    {dest.name}: {written / 1024 / 1024:.0f} MB"
                                    f" / {total / 1024 / 1024:.0f} MB ({percent:.1f}%)",
                                    flush=True,
                                )
                            else:
                                print(
                                    f"    {dest.name}: {written / 1024 / 1024:.0f} MB",
                                    flush=True,
                                )
                            last_report = now

            print(f"    done: {dest.name} ({dest.stat().st_size:,} bytes)", flush=True)
            return
        except Exception as exc:  # noqa: BLE001
            print(f"    attempt {attempt}/{retries} failed: {exc}", flush=True)
            if attempt == retries:
                raise
            time.sleep(3 * attempt)


def main() -> int:
    for name, spec in MODELS.items():
        target = ROOT / name
        print(f"==> {name} -> {target}", flush=True)
        for relative in spec["files"]:
            dest = target / relative
            url = f"{spec['url'].rstrip('/')}/{relative}"
            print(f"  {relative}", flush=True)
            download_file(url, dest)

    print("== 下载完成 ==")
    for name in MODELS:
        target = ROOT / name
        total = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
        print(f"  {target}: {total / 1024 / 1024 / 1024:.2f} GB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
