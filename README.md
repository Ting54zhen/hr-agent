# HR 知识库智能问答 Agent

一个可落地的 HR Agent 示例：**RAG 知识库 + MCP 数据工具 + LangGraph 状态机 + FastAPI SSE 流式输出**。

[![HR 助手界面](docs/assets/chat-answer.png)](https://ting54zhen.github.io/hr-agent/)

> 演示主页：<https://ting54zhen.github.io/hr-agent/>

- 制度类问题：从 HR 文档中混合检索（BM25 + BGE-M3 向量），再经 BGE reranker 重排。
- 个人数据问题：通过 MCP Server 查询 MySQL 中的假期余额、考勤、组织信息。
- 混合问题：同时走 RAG 和 MCP，再统一生成。
- 每次回答都做事实校验；不通过时重试一次，仍不通过则明确兜底，不编造。
- 会话通过 Redis checkpoint 持久化。

> `data/docs/` 中的文档是演示数据，不是真实公司制度。

## 架构

```text
用户
 │
 ▼
FastAPI /chat (SSE)
 │
 ▼
LangGraph StateGraph
 ├─ router          判断 policy / data / mixed / chitchat
 ├─ retrieve        BM25 + BGE-M3 → RRF → bge-reranker Top-5
 ├─ agent           LLM + MCP 工具（查假期/考勤/组织）
 ├─ tools           MCP Server → MySQL（只读 + 白名单 + 审计）
 ├─ generate        基于资料/工具结果生成回答，带引用
 ├─ check           事实校验；不通过则重试，仍不通过走 fallback
 └─ fallback        “根据现有资料无法确认”
 │
 ▼
Redis AsyncRedisSaver（按 session_id 保存多轮会话）
```

## 目录

```text
hr-agent/
├─ app/
│  ├─ main.py                 FastAPI + SSE + 生命周期
│  ├─ auth.py                 登录校验 + HMAC Token
│  ├─ config.py               .env 配置
│  ├─ rag/
│  │  ├─ ingest.py            解析 → 标题切分 → 500/80 chunk → BGE-M3 → Chroma
│  │  └─ retriever.py         BM25 + 向量 + RRF + reranker
│  ├─ mcp_server/
│  │  ├─ server.py            FastMCP：四个只读工具
│  │  └─ db.py                MySQL 连接
│  └─ agent/
│     ├─ graph.py             LangGraph 状态机
│     ├─ prompts.py           路由/生成/校验 Prompt
│     └─ tools.py             langchain-mcp-adapters 加载 MCP 工具
├─ data/docs/                 示例 HR 文档
├─ scripts/
│  ├─ seed_db.sql             MySQL 建表 + 示例数据（含 users 表）
│  ├─ seed_users.py           创建 users 表 / 重置账号密码
│  ├─ download_models_modelscope.py  ModelScope 下载 BGE 模型（推荐）
│  ├─ download_models.py      HuggingFace 镜像下载（备用）
│  ├─ check_env.py            环境自检
│  ├─ smoke_test.py           MCP + RAG 冒烟测试
│  ├─ chat_cli.py             命令行测 /chat（SSE）
│  └─ search_cli.py           命令行测 /search
├─ web/
│  └─ index.html              浏览器聊天页（/ui/ 或双击打开）
├─ docs/
│  └─ index.html              GitHub Pages 演示主页
├─ eval/                      检索评测集与脚本
├─ docker-compose.yml         MySQL 8.4 + Redis 8
└─ .env.example
```

## 环境

本机已按 D 盘优先配置：

| 组件 | 路径/版本 |
|---|---|
| Python | `D:\Dev\Python312`（3.12.10） |
| uv | `D:\Dev\Python312\Scripts\uv.exe` |
| Git | `D:\Dev\Git` |
| Node | `D:\Dev\node` |
| Docker Desktop | `D:\Dev\DockerDesktop` |
| Docker WSL 数据 | `D:\Docker\data` |
| HF 模型缓存 | `D:\Dev\cache\huggingface` |
| BGE 模型 | `D:\Dev\models\bge-m3`、`D:\Dev\models\bge-reranker-v2-m3` |
| 项目 | `D:\ClaudeCode\hr-agent` |

Python 依赖已装在项目 `.venv`，PyTorch 为 CPU 版。需要重新安装时：

```powershell
cd D:\ClaudeCode\hr-agent
D:\Dev\Python312\Scripts\uv.exe sync
```

## 快速开始

### 1. 启动 MySQL / Redis

```powershell
cd D:\ClaudeCode\hr-agent
docker compose up -d
docker compose ps
```

如果 `docker` 命令找不到，把 `D:\Dev\DockerDesktop\resources\bin` 加到 PATH 前面。

MySQL 首次启动会执行 `scripts/seed_db.sql`。如果发现中文乱码，用 UTF-8 客户端重新导入：

```powershell
cmd /c "docker exec -i hr-mysql mysql -uroot -proot --default-character-set=utf8mb4 < scripts\seed_db.sql"
```

PowerShell 不支持 `<` 重定向，必须套 `cmd /c`；也不要用 `Get-Content | docker exec`，PowerShell 5.1 会把 UTF-8 中文转坏。Git Bash 下可直接写 `docker exec -i hr-mysql mysql -uroot -proot --default-character-set=utf8mb4 < scripts/seed_db.sql`。

### 2. 配置 LLM

复制 `.env.example` 为 `.env`，填入 Key：

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=deepseek-chat
OPENAI_API_KEY=sk-你的key
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

也支持 Claude：

```dotenv
LLM_PROVIDER=anthropic
LLM_MODEL=claude-opus-5-5
ANTHROPIC_API_KEY=sk-ant-你的key
```

`.env` 已被 `.gitignore` 忽略，不要提交。

### 3. 下载模型（约 4.5GB）

国内网络推荐 ModelScope（魔搭）：

```powershell
.\.venv\Scripts\python.exe scripts\download_models_modelscope.py
```

下载到 `D:\Dev\models\bge-m3` 和 `D:\Dev\models\bge-reranker-v2-m3`，`.env` 已指向这两个目录。

也可以用 HuggingFace 镜像：

```powershell
.\.venv\Scripts\python.exe scripts\download_models.py
```

HF 脚本会读取 `.env` 中的 `HF_HOME` / `HF_ENDPOINT`，并默认关闭 Xet。若 hf-mirror 仍返回 401 或超时，直接用 ModelScope 脚本。

### 4. 文档入库

```powershell
.\.venv\Scripts\python.exe -m app.rag.ingest
```

输出：

- `data/chunks.jsonl`：切分后的片段
- `data/chroma/`：Chroma 持久化向量库

重新入库会清空旧集合；保留旧数据用 `--no-reset`。

### 5. 启动服务

```powershell
.\.venv\Scripts\python.exe -m app.main
```

或：

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```

打开 <http://127.0.0.1:8000/docs> 查看接口。

### 6. 自检

```powershell
.\.venv\Scripts\python.exe scripts\check_env.py
```

`/health` 会返回：

```json
{
  "status": "ok",
  "llm_configured": true,
  "graph_ready": true,
  "checkpointer": "redis",
  "chunks": 48,
  "tools": ["get_leave_balance", "get_attendance", "get_employee_profile", "get_org_info"]
}
```

## 接口

### 登录与 `users` 表

演示账号：`1001` 张三 / `1002` 李四 / `1003` 王五，初始密码均为 `123456`。

账号密码存放在 MySQL `users` 表，使用 **PBKDF2-SHA256（600,000 次迭代，每个账号独立随机盐）** 哈希，不保存明文：

| 字段 | 说明 |
|---|---|
| `employee_id` | 主键，关联 `employees.id` |
| `password_hash` | `pbkdf2_sha256$迭代次数$盐$哈希` |
| `is_active` | 0 表示禁止登录 |
| `created_at` | 创建时间 |
| `last_login_at` | 最近登录时间 |

首次建库由 `scripts/seed_db.sql` 写入。已有数据库执行：

```powershell
.\.venv\Scripts\python.exe scripts\seed_users.py

# 重置某个账号的密码
.\.venv\Scripts\python.exe scripts\seed_users.py --ids 1001 --password 新密码 --reset
```

> 新增员工需要同时写入 `employees`、`users`，并加入 `HR_ALLOWED_IDS`（MCP 的二次白名单）；把 `users.is_active` 置为 0 可禁止该账号登录。

### `POST /auth/login`

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"employee_id":1001,"password":"123456"}'
```

返回 `access_token`、`token_type`、`expires_in` 和 `user`。登录后访问 `/chat` 需要携带：

```text
Authorization: Bearer <access_token>
```

`GET /auth/me` 用于校验登录态。Token 是 HMAC 签名实现，密钥由 `HR_AUTH_SECRET` 控制；生产环境建议改用 argon2/bcrypt、增加登录限流，并通过 HTTPS 传输。

### `POST /chat`（SSE，需要登录）

```bash
curl -N -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"message":"我还有几天年假？","session_id":"demo-1"}'
```

事件序列：

```text
event: meta      {"session_id":"demo-1","employee_id":1001}
event: token     {"text":"你"}
event: token     {"text":"目前"}
...
event: done      {"answer":"...","route":"data","grounded":true,"sources":[...]}
```

- `token` 用于前端逐字渲染。
- 如果事实校验失败并重试，会先收到 `event: reset`，前端应清空当前回答。
- `done` 同时带完整 `answer`，可作为兜底。

打开 <http://127.0.0.1:8000/ui/>（或直接双击 `web/index.html`），用演示账号登录后使用聊天页，或运行

```powershell
.\.venv\Scripts\python.exe scripts\chat_cli.py "我还有几天年假？"
```

### `POST /search`（只测检索，不调用 LLM）

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"年假没休完可以结转吗","top_k":5}'
```

没有 API Key 时也可以用它验证 RAG 召回。

### 演示问题

| 类型 | 问题 | 预期 |
|---|---|---|
| policy | 年假没休完可以结转到什么时候？ | 引用《示例-假期管理制度》 |
| policy | 迟到 30 分钟以内怎么处理？ | 引用《示例-考勤与远程办公制度》 |
| data | 我还有几天年假？ | 调 `get_leave_balance`，返回 7 天 |
| data | 我上个月迟到几次？ | 调 `get_attendance`，返回 2026-10 有 1 次迟到 |
| mixed | 我今年还剩几天年假，离职时怎么折算？ | 先查余额，再引用折算规则 |
| 无答案 | 公司食堂几点开饭？ | 明确说资料中无法确认 |

## RAG 细节

1. **解析**：PDF 用 PyMuPDF，DOCX 用 python-docx（保留 Heading 层级），Markdown/TXT 直接读取。
2. **切分**：先按 Markdown 标题切 section，再用 `RecursiveCharacterTextSplitter` 切 500 token、overlap 80。
3. **向量化**：`BAAI/bge-m3`，CPU，`normalize_embeddings=True`，写入 Chroma。
4. **召回**：dense Top-20 + BM25 Top-20。
5. **融合**：RRF（k=60）。
6. **重排**：`BAAI/bge-reranker-v2-m3`，取 Top-5。
7. **引用**：Prompt 要求标注 `[来源: 文件名 / 标题]`。
8. **兜底**：资料不足时明确说无法确认，不猜测。

调参位置：`app/rag/ingest.py` 的 `chunk_size` / `chunk_overlap`，`app/rag/retriever.py` 的 `RRF_K` / Confidence 阈值，以及 `.env`：

```dotenv
# 进入 reranker 的候选数；CPU 上重排是主要耗时
RETRIEVAL_RECALL_K=10
RERANK_MAX_LENGTH=512
RERANK_BATCH_SIZE=8
```

本机 CPU 实测：20 个候选单次检索 17–22 s，10 个候选 6–11 s，两者 Recall@5 / MRR 相同。

## MCP 设计

`app/mcp_server/server.py` 暴露四个工具：

| 工具 | 作用 | 关键点 |
|---|---|---|
| `get_leave_balance` | 年假/病假余额 | 只读、按工号白名单 |
| `get_attendance` | 月度考勤明细与汇总 | 校验 `YYYY-MM` |
| `get_employee_profile` | 按工号查部门、邮箱、直属上级 | “我的部门/上级”走这个工具 |
| `get_org_info` | 按姓名查组织信息 | 查到人后再校验可见性 |

安全措施：

- **只读**：不提供任意 SQL 工具，避免 Prompt 注入后执行写操作。
- **服务端鉴权**：`HR_ALLOWED_IDS` 在 MCP Server 内校验，不信任模型传入的工号。
- **行级权限**：`get_employee_profile` 先校验工号白名单；`get_org_info` 查到人后再次过滤允许的工号。
- **审计**：每次调用写入 `logs/mcp_audit.jsonl`，包含时间、工具、工号、参数、成功/失败。
- **错误脱敏**：不把 SQL 异常和数据库结构返回给模型。

真实项目中，`employee_id` 应来自登录态（JWT/Session），而不是让前端或模型随意传。

## LangGraph 状态

`app/agent/graph.py` 的 `AgentState`：

```python
messages      # add_messages 累积多轮消息
employee_id   # 当前登录员工
route         # policy / data / mixed / chitchat
context       # 检索到的资料
sources       # 引用来源
retry_count   # 事实校验重试次数
grounded      # 是否通过校验
check_reason  # 校验理由
```

关键边：

```text
router ──policy──> retrieve ──> generate ──> check ──pass──> END
   │                                  ▲          │
   ├──data──> agent ──tool_calls──> tools        │fail（最多 1 次）
   │            └────no tool────> generate ──────┘
   └──mixed─> retrieve ──> agent ──> generate ──> check
```

## 评测

`eval/qa.jsonl` 包含 50 条问题，覆盖 policy / data / mixed / 无答案。

只测检索（不需要 LLM Key）：

```powershell
.\.venv\Scripts\python.exe eval\run_eval.py
```

本机实测（35 条 policy 类问题，48 个 chunk）：**Recall@5 = 100%，MRR = 0.9714**。

输出 `Recall@5`、`MRR`，以及每条问题命中的文档。需要保存结果时：

```powershell
.\.venv\Scripts\python.exe eval\run_eval.py --output D:\ClaudeCode\数据\hr-agent-检索评测结果.json
```

## 常见问题

### 模型下载 401 / Xet 错误

hf-mirror 不支持 Xet 的重建接口。确保：

```dotenv
HF_HUB_DISABLE_XET=1
HF_ENDPOINT=https://hf-mirror.com
```

然后重新运行 `scripts/download_models.py`，已下载的分片会复用。

### `/chat` 返回 503

看 `/health` 的 `startup_error`：

- `graph: LLM 未配置`：`.env` 里没有填 Key，或 Key 还是占位符。
- `mcp: ...`：MCP Server 启动失败，检查 `.venv`、MySQL 和 `HR_ALLOWED_IDS`。
- `retriever: ...`：模型没下载完，或 Chroma 目录损坏。

### 中文乱码

MySQL 导入时没指定客户端编码。用上面的 `--default-character-set=utf8mb4` 重新执行 `seed_db.sql`。

### Windows 控制台中文乱码

只是终端编码问题，不影响接口。可先执行：

```powershell
chcp 65001
$env:PYTHONIOENCODING="utf-8"
```

### Docker 路径

本项目 Docker 数据在 `D:\Docker\data`。如果 Docker Desktop 启动失败，先确认没有旧版 WSL 发行版占用 VHDX：

```powershell
wsl -l -v
docker context ls
```

## 面试可讲的点

- 为什么 RAG 要 hybrid：BM25 对制度编号、专有名词更稳，向量对同义表达更好；RRF 不需要调分数尺度。
- 为什么要 reranker：召回阶段追求高 recall，rerank 阶段用 cross-encoder 提升 precision。
- MCP 和 function calling 的区别：MCP 是协议/进程边界，工具由独立 Server 提供，可复用、可审计；function calling 是模型输出工具调用的机制。
- 为什么要事实校验：RAG 仍可能把检索到的相邻条款拼接错；check 节点用结构化输出判断 grounded，不通过重试或兜底。
- 权限为什么放服务端：模型可能被 Prompt 注入诱导查询他人数据，白名单必须在 MCP Server 内执行。
- Redis checkpoint 的作用：按 `thread_id` 保存多轮消息，服务重启后会话可恢复；也方便做人工审批中断。
