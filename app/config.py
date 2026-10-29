"""HR Agent 配置。

所有配置都从项目根目录的 .env 读取；不把 Key 写进代码。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "openai"
    llm_model: str = "deepseek-chat"
    openai_api_key: str = ""
    openai_base_url: str = ""
    anthropic_api_key: str = ""

    # 本地模型
    embed_model: str = "BAAI/bge-m3"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    hf_home: str = "D:/Dev/cache/huggingface"
    hf_endpoint: str = "https://hf-mirror.com"
    hf_hub_disable_xet: str = "1"

    # 检索/重排（CPU 上重排是主要耗时，候选数越小越快）
    retrieval_recall_k: int = 10
    rerank_max_length: int = 512
    rerank_batch_size: int = 8

    # 存储
    redis_url: str = "redis://localhost:6379/0"
    chroma_dir: str = "data/chroma"
    log_dir: str = "logs"

    # MySQL
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "hr"
    mysql_password: str = "hr"
    mysql_database: str = "hr"

    # MCP 权限：真实项目应从登录态/工号映射获取，不能由模型传入
    hr_allowed_ids: str = "1001,1002,1003"

    # 登录：账号密码存放在 MySQL users 表（PBKDF2 哈希）
    hr_auth_secret: str = "dev-only-change-me"
    hr_auth_token_ttl_hours: int = 12

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def chroma_path(self) -> Path:
        path = Path(self.chroma_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def logs_path(self) -> Path:
        path = Path(self.log_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def docs_path(self) -> Path:
        return PROJECT_ROOT / "data" / "docs"

    @property
    def chunks_path(self) -> Path:
        return PROJECT_ROOT / "data" / "chunks.jsonl"

    @property
    def allowed_ids(self) -> set[int]:
        ids: set[int] = set()
        for part in self.hr_allowed_ids.split(","):
            part = part.strip()
            if part.isdigit():
                ids.add(int(part))
        return ids

    @property
    def llm_configured(self) -> bool:
        if self.llm_provider.lower() == "anthropic":
            key = self.anthropic_api_key
            return bool(key and not key.startswith("sk-ant-your"))
        key = self.openai_api_key
        return bool(key and not key.startswith("sk-your"))


settings = Settings()

# huggingface_hub / sentence-transformers 在 import 时读取这些环境变量。
os.environ.setdefault("HF_HOME", settings.hf_home)
os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)
os.environ.setdefault("HF_HUB_DISABLE_XET", settings.hf_hub_disable_xet)
