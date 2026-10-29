"""创建 MySQL users 表并写入演示账号（PBKDF2 密码哈希）。

用法：
    python scripts/seed_users.py
    python scripts/seed_users.py --ids 1001 --password newpass --reset
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.auth import hash_password  # noqa: E402
from app.mcp_server.db import cursor  # noqa: E402

CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
  employee_id INT PRIMARY KEY,
  password_hash VARCHAR(255) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP NULL DEFAULT NULL,
  CONSTRAINT fk_users_employee FOREIGN KEY (employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def parse_ids(text: str) -> list[int]:
    ids: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            raise ValueError(f"工号格式不正确：{part}")
        ids.append(int(part))
    if not ids:
        raise ValueError("至少需要一个工号")
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description="创建 users 表并写入演示账号")
    parser.add_argument("--ids", default="1001,1002,1003", help="逗号分隔的工号")
    parser.add_argument("--password", default="123456", help="设置的密码，至少 6 位")
    parser.add_argument("--reset", action="store_true", help="覆盖已存在账号的密码")
    args = parser.parse_args()

    if len(args.password) < 6:
        print("密码至少需要 6 位", file=sys.stderr)
        return 1

    try:
        employee_ids = parse_ids(args.ids)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        with cursor() as cur:
            cur.execute(CREATE_USERS_SQL)

            placeholders = ",".join(["%s"] * len(employee_ids))
            cur.execute(
                f"SELECT id FROM employees WHERE id IN ({placeholders})",
                tuple(employee_ids),
            )
            existing = {int(row["id"]) for row in cur.fetchall()}
            missing = [emp_id for emp_id in employee_ids if emp_id not in existing]
            if missing:
                print(
                    f"employees 表中不存在这些工号：{missing}，请先导入 scripts/seed_db.sql",
                    file=sys.stderr,
                )
                return 1

            if args.reset:
                sql = """
                INSERT INTO users (employee_id, password_hash, is_active)
                VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE
                  password_hash = VALUES(password_hash),
                  is_active = 1
                """
            else:
                sql = """
                INSERT IGNORE INTO users (employee_id, password_hash, is_active)
                VALUES (%s, %s, 1)
                """

            for employee_id in employee_ids:
                cur.execute(sql, (employee_id, hash_password(args.password)))

            cur.execute(
                "SELECT employee_id, is_active, last_login_at FROM users ORDER BY employee_id"
            )
            rows = cur.fetchall()
    except Exception as exc:  # noqa: BLE001
        print(f"写入 users 表失败：{exc}", file=sys.stderr)
        print("请确认 MySQL 已启动：docker compose up -d", file=sys.stderr)
        return 1

    action = "已重置" if args.reset else "已写入（已存在的账号保持不变）"
    print(f"{action}：{', '.join(str(emp_id) for emp_id in employee_ids)}")
    print("当前 users 表：")
    for row in rows:
        last_login = row.get("last_login_at") or "-"
        print(
            f"  {row['employee_id']}  active={row['is_active']}  last_login={last_login}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
