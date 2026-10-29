"""命令行测试 /chat 的 SSE 输出。

用法：
    python scripts/chat_cli.py "我还有几天年假？"
    python scripts/chat_cli.py "年假可以结转吗？" --session demo-2 --employee 1002
"""

from __future__ import annotations

import argparse
import json
import sys

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description="测试 HR Agent 的 /chat 流式接口")
    parser.add_argument("question", help="要问的问题")
    parser.add_argument("--session", default="demo-1", help="会话 ID，同一个 ID 共享上下文")
    parser.add_argument("--employee", type=int, default=1001, help="登录工号")
    parser.add_argument("--password", default="123456", help="登录密码（演示账号）")
    parser.add_argument("--token", default="", help="已有 Bearer Token，填写后跳过登录")
    parser.add_argument("--url", default="http://127.0.0.1:8000/chat")
    args = parser.parse_args()

    base_url = args.url.rsplit("/chat", 1)[0]
    token = args.token.strip()

    if not token:
        try:
            login = requests.post(
                base_url + "/auth/login",
                json={"employee_id": args.employee, "password": args.password},
                timeout=15,
            )
        except requests.RequestException as exc:
            print(f"连不上服务：{exc}", file=sys.stderr)
            print("先在另一个终端运行：python -m app.main", file=sys.stderr)
            return 1

        if login.status_code != 200:
            try:
                detail = login.json().get("detail", login.text)
            except ValueError:
                detail = login.text
            print(f"登录失败（HTTP {login.status_code}）：{detail}", file=sys.stderr)
            return 1

        data = login.json()
        token = data.get("access_token", "")
        user = data.get("user") or {}
        print(f"登录：{user.get('name') or args.employee}（工号 {args.employee}）")

    payload = {
        "message": args.question,
        "session_id": args.session,
    }

    try:
        response = requests.post(
            args.url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            stream=True,
            timeout=300,
        )
    except requests.RequestException as exc:
        print(f"连不上服务：{exc}", file=sys.stderr)
        print("先在另一个终端运行：python -m app.main", file=sys.stderr)
        return 1

    if response.status_code != 200:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        print(f"HTTP {response.status_code}：{detail}", file=sys.stderr)
        if response.status_code == 401:
            print("登录已失效，请去掉 --token 重新登录。", file=sys.stderr)
        return 1

    event = ""
    sources: list[str] = []
    print("回答：", end="", flush=True)

    for raw in response.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        if raw.startswith("event:"):
            event = raw.split(":", 1)[1].strip()
            continue
        if not raw.startswith("data:"):
            continue

        data = json.loads(raw.split(":", 1)[1].strip())

        if event == "token":
            print(data.get("text", ""), end="", flush=True)
        elif event == "reset":
            print("\n\n[事实校验未通过，重新生成]\n回答：", end="", flush=True)
        elif event == "meta":
            print(
                f"[session={data.get('session_id')} "
                f"employee={data.get('employee_id')}]\n回答：",
                end="",
                flush=True,
            )
        elif event == "done":
            sources = [str(item) for item in data.get("sources") or []]
            print(
                f"\n\n[route={data.get('route')} "
                f"grounded={data.get('grounded')} "
                f"retry={data.get('retry_count')}]"
            )
            if data.get("check_reason"):
                print(f"[校验理由] {data.get('check_reason')}")
            if sources:
                print("[来源]")
                for item in sources:
                    print(f"  - {item}")
            if not data.get("answer"):
                print("（服务端没有返回完整答案，请查看日志）")
        elif event == "error":
            print(f"\n[错误] {data.get('message')}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
