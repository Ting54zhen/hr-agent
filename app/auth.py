"""登录模块：MySQL users 表 + PBKDF2 密码哈希 + HMAC 签名 Token。

生产环境建议把 PBKDF2 换成 argon2/bcrypt，并配合 HTTPS 与登录限流。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.mcp_server.db import cursor

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)
PBKDF2_ITERATIONS = 600_000


class AuthStorageError(RuntimeError):
    """用户表不可用时抛出，避免把数据库故障误报成密码错误。"""


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str) -> str:
    digest = hmac.new(
        settings.hr_auth_secret.encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def create_access_token(
    employee_id: int,
    name: str,
    department: str,
    email: str = "",
    ttl_seconds: int | None = None,
) -> str:
    ttl = ttl_seconds if ttl_seconds is not None else settings.hr_auth_token_ttl_hours * 3600
    issued_at = int(time.time())
    payload = {
        "sub": int(employee_id),
        "name": name,
        "department": department,
        "email": email,
        "iat": issued_at,
        "exp": issued_at + ttl,
    }
    body = _b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    return f"{body}.{_sign(body)}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        body, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _sign(body)):
            return None
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except Exception:  # noqa: BLE001 - 任何格式错误都视为无效 Token
        return None

    if not isinstance(payload, dict) or "sub" not in payload:
        return None
    try:
        if int(payload.get("exp", 0)) <= int(time.time()):
            return None
        payload["sub"] = int(payload["sub"])
    except (TypeError, ValueError):
        return None
    return payload


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        if iterations <= 0:
            return False
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
    except (TypeError, ValueError):
        logger.warning("密码哈希格式无效")
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def _fetch_user(employee_id: int) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute(
            """
            SELECT u.employee_id, u.password_hash, u.is_active,
                   e.name, e.department, e.email
            FROM users u
            JOIN employees e ON e.id = u.employee_id
            WHERE u.employee_id = %s
            """,
            (employee_id,),
        )
        return cur.fetchone()


def authenticate(employee_id: int, password: str) -> dict[str, Any] | None:
    if employee_id not in settings.allowed_ids:
        return None

    try:
        row = _fetch_user(employee_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("读取 users 表失败")
        raise AuthStorageError("用户表不可用") from exc

    if not row or not row.get("is_active"):
        return None
    if not verify_password(password, str(row["password_hash"])):
        return None

    try:
        with cursor() as cur:
            cur.execute(
                "UPDATE users SET last_login_at = NOW() WHERE employee_id = %s",
                (employee_id,),
            )
    except Exception:  # noqa: BLE001
        logger.warning("更新 users.last_login_at 失败", exc_info=True)

    logger.info("登录成功：employee_id=%s", employee_id)
    return {
        "employee_id": int(row["employee_id"]),
        "name": row["name"],
        "department": row["department"],
        "email": row.get("email") or "",
    }


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
