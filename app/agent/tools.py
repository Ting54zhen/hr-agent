"""通过 langchain-mcp-adapters 加载 MCP Server 的工具。"""

from __future__ import annotations

import logging
import os
import sys

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import PROJECT_ROOT, settings

logger = logging.getLogger(__name__)


def _stdio_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(PROJECT_ROOT),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
            "HR_ALLOWED_IDS": settings.hr_allowed_ids,
            "MYSQL_HOST": settings.mysql_host,
            "MYSQL_PORT": str(settings.mysql_port),
            "MYSQL_USER": settings.mysql_user,
            "MYSQL_PASSWORD": settings.mysql_password,
            "MYSQL_DATABASE": settings.mysql_database,
            "LOG_DIR": settings.log_dir,
        }
    )
    return env


def mcp_connections() -> dict:
    return {
        "hr": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "app.mcp_server.server"],
            "env": _stdio_env(),
            "cwd": str(PROJECT_ROOT),
        }
    }


async def load_hr_tools() -> list[BaseTool]:
    """每次调用都会启动一个 stdio MCP Server 进程，工具调用本身是无状态的。"""
    client = MultiServerMCPClient(mcp_connections())
    tools = await client.get_tools()
    logger.info("已加载 MCP 工具：%s", [tool.name for tool in tools])
    return tools
