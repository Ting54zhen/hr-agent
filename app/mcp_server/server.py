"""HR 数据 MCP Server（stdio）。

只暴露只读工具，并在服务端做员工白名单校验和审计日志。
启动：python -m app.mcp_server.server
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# 允许以文件路径直接启动（mcp run / mcp dev 都是这样），
# 不依赖调用方提前设置 PYTHONPATH。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.config import settings  # noqa: E402
from app.mcp_server.db import cursor

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("hr-mcp")

mcp = FastMCP("hr-data-server")


def _audit(
    tool: str,
    employee_id: int | None,
    params: dict[str, Any],
    ok: bool,
    error: str | None = None,
) -> None:
    try:
        settings.logs_path.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "employee_id": employee_id,
            "params": params,
            "ok": ok,
        }
        if error:
            record["error"] = error
        with (settings.logs_path / "mcp_audit.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        logger.exception("写审计日志失败")


def _ensure_allowed(employee_id: int) -> None:
    if employee_id not in settings.allowed_ids:
        raise PermissionError(f"没有权限查询员工 {employee_id} 的数据")


def _format_time(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
        return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"
    return str(value)[:5]


@mcp.tool()
def get_leave_balance(employee_id: int) -> dict[str, Any]:
    """查询指定员工的年假、病假总额、已用和剩余天数。

    Args:
        employee_id: 员工工号，例如 1001。
    """
    params = {"employee_id": employee_id}
    try:
        _ensure_allowed(employee_id)
        with cursor() as cur:
            cur.execute(
                """
                SELECT e.id, e.name, e.department,
                       l.annual_total, l.annual_used,
                       l.sick_total, l.sick_used
                FROM employees e
                JOIN leave_balances l ON l.employee_id = e.id
                WHERE e.id = %s
                """,
                (employee_id,),
            )
            row = cur.fetchone()
        if not row:
            _audit("get_leave_balance", employee_id, params, False, "not_found")
            return {"ok": False, "error": "未找到该员工的假期记录"}

        row["annual_remaining"] = row["annual_total"] - row["annual_used"]
        row["sick_remaining"] = row["sick_total"] - row["sick_used"]
        _audit("get_leave_balance", employee_id, params, True)
        return {"ok": True, "data": row}
    except PermissionError as exc:
        _audit("get_leave_balance", employee_id, params, False, str(exc))
        return {"ok": False, "error": str(exc)}
    except Exception:  # noqa: BLE001
        logger.exception("get_leave_balance failed")
        _audit("get_leave_balance", employee_id, params, False, "internal_error")
        return {"ok": False, "error": "查询假期余额失败，请稍后重试"}


@mcp.tool()
def get_attendance(employee_id: int, month: str = "") -> dict[str, Any]:
    """查询指定员工某个月的考勤明细和汇总。

    Args:
        employee_id: 员工工号，例如 1001。
        month: 月份，格式 YYYY-MM，例如 2026-10；留空表示当前月。
    """
    month = month.strip() or datetime.now().strftime("%Y-%m")
    params = {"employee_id": employee_id, "month": month}
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        return {"ok": False, "error": "month 必须使用 YYYY-MM 格式"}

    try:
        _ensure_allowed(employee_id)
        with cursor() as cur:
            cur.execute(
                """
                SELECT work_date, status, check_in, check_out
                FROM attendance
                WHERE employee_id = %s AND DATE_FORMAT(work_date, '%%Y-%%m') = %s
                ORDER BY work_date
                """,
                (employee_id, month),
            )
            rows = cur.fetchall()

        summary: dict[str, int] = {}
        for row in rows:
            status = row["status"]
            summary[status] = summary.get(status, 0) + 1
            if row["work_date"] is not None:
                row["work_date"] = row["work_date"].isoformat()
            row["check_in"] = _format_time(row["check_in"])
            row["check_out"] = _format_time(row["check_out"])

        _audit("get_attendance", employee_id, params, True)
        return {
            "ok": True,
            "data": {
                "employee_id": employee_id,
                "month": month,
                "summary": summary,
                "records": rows,
            },
        }
    except PermissionError as exc:
        _audit("get_attendance", employee_id, params, False, str(exc))
        return {"ok": False, "error": str(exc)}
    except Exception:  # noqa: BLE001
        logger.exception("get_attendance failed")
        _audit("get_attendance", employee_id, params, False, "internal_error")
        return {"ok": False, "error": "查询考勤失败，请稍后重试"}


@mcp.tool()
def get_employee_profile(employee_id: int) -> dict[str, Any]:
    """查询指定员工的组织信息：工号、姓名、部门、邮箱、直属上级。

    Args:
        employee_id: 员工工号，例如 1001。
    """
    params = {"employee_id": employee_id}
    try:
        _ensure_allowed(employee_id)
        with cursor() as cur:
            cur.execute(
                """
                SELECT e.id, e.name, e.department, e.email,
                       m.name AS manager_name
                FROM employees e
                LEFT JOIN employees m ON m.id = e.manager_id
                WHERE e.id = %s
                """,
                (employee_id,),
            )
            row = cur.fetchone()
        if not row:
            _audit("get_employee_profile", employee_id, params, False, "not_found")
            return {"ok": False, "error": "未找到该员工的组织信息"}
        _audit("get_employee_profile", employee_id, params, True)
        return {"ok": True, "data": row}
    except PermissionError as exc:
        _audit("get_employee_profile", employee_id, params, False, str(exc))
        return {"ok": False, "error": str(exc)}
    except Exception:  # noqa: BLE001
        logger.exception("get_employee_profile failed")
        _audit("get_employee_profile", employee_id, params, False, "internal_error")
        return {"ok": False, "error": "查询员工信息失败，请稍后重试"}


@mcp.tool()
def get_org_info(name: str) -> dict[str, Any]:
    """按姓名查询员工的组织信息：工号、部门、邮箱、直属上级。

    Args:
        name: 员工姓名，例如 张三。
    """
    name = name.strip()
    params = {"name": name}
    if not name:
        return {"ok": False, "error": "姓名不能为空"}

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT e.id, e.name, e.department, e.email,
                       m.name AS manager_name
                FROM employees e
                LEFT JOIN employees m ON m.id = e.manager_id
                WHERE e.name = %s
                """,
                (name,),
            )
            rows = cur.fetchall()

        visible = [row for row in rows if row["id"] in settings.allowed_ids]
        if not visible:
            _audit("get_org_info", None, params, False, "not_found_or_forbidden")
            return {"ok": False, "error": "未找到该员工，或没有查询权限"}

        _audit("get_org_info", visible[0]["id"], params, True)
        return {"ok": True, "data": visible}
    except Exception:  # noqa: BLE001
        logger.exception("get_org_info failed")
        _audit("get_org_info", None, params, False, "internal_error")
        return {"ok": False, "error": "查询组织信息失败，请稍后重试"}


if __name__ == "__main__":
    mcp.run(transport="stdio")

@mcp.tool()
def get_pending_leaves(employee_id: int) -> dict[str, Any]:
    """查询指定员工所有待审批的请假申请。

    当用户问“我的请假批了吗”“我还有哪些假没批”时使用。

    Args:
        employee_id: 员工工号，例如 1001。
    """
    params = {"employee_id": employee_id}
    try:
        _ensure_allowed(employee_id)
        with cursor() as cur:
            cur.execute(
                """
                SELECT id, leave_type, start_date, end_date, status
                FROM leave_requests
                WHERE employee_id = %s AND status = 'pending'
                ORDER BY start_date
                """,
                (employee_id,),
            )
            rows = cur.fetchall()
        for row in rows:
            row["start_date"] = str(row["start_date"])
            row["end_date"] = str(row["end_date"])
        _audit("get_pending_leaves", employee_id, params, True)
        return {"ok": True, "data": {"pending": rows, "count": len(rows)}}
    except PermissionError as exc:
        _audit("get_pending_leaves", employee_id, params, False, str(exc))
        return {"ok": False, "error": str(exc)}
    except Exception:  # noqa: BLE001
        logger.exception("get_pending_leaves failed")
        _audit("get_pending_leaves", employee_id, params, False, "internal_error")
        return {"ok": False, "error": "查询请假申请失败，请稍后重试"}
