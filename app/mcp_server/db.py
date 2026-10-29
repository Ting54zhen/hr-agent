"""MySQL 连接（只读查询用）。"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pymysql
from pymysql.cursors import DictCursor

from app.config import settings


def get_connection() -> pymysql.Connection:
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=5,
        read_timeout=10,
    )


@contextmanager
def cursor() -> Iterator[DictCursor]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()
