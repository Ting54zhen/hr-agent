# HR 知识库智能问答 Agent：手把手操作手册

> 对应简历项目：**HR 知识库智能问答 Agent｜独立开发｜Python / LangChain / LangGraph / MCP**
>
> 本机成品已在：`D:\ClaudeCode\hr-agent`
>
> 这份手册按「精确到步骤」写：每一步只有**一个动作**，写清楚**在哪个软件里、点哪里、输入什么、看到什么算成功**。

---

## 怎么用这份手册

- 第 0 章到第 9 章：**照着做**，每章结尾有 ✅ 完成标志，没达到就不要往下走。
- 第 10 章到第 12 章：**看懂 + 动手改**，用来应付面试追问。
- 第 13 章到第 15 章：评测、排错、讲解话术。
- 全流程约 6–8 小时，其中下载模型 45–60 分钟可以挂着干别的。

本机已经全部装好、跑通过，所以你做的时候大概率是「验证」而不是「安装」。换一台电脑时，从第 0 章开始也能完整复现。

---

# 第 0 章 软件清单：装什么、装在哪、怎么确认装好了

## 0.1 一张表看清全部软件

| # | 软件 | 干什么用 | 本机位置 | 是否必须 |
|---|---|---|---|---|
| 1 | VS Code | 写代码、开终端、调试、看文件 | 系统默认位置（用户级） | 必须 |
| 2 | Python 3.12 | 运行项目 | `D:\Dev\Python312` | 必须 |
| 3 | uv | 装 Python 依赖、锁版本 | `D:\Dev\Python312\Scripts\uv.exe` | 必须 |
| 4 | Git | 版本管理、传 GitHub | `D:\Dev\Git` | 建议 |
| 5 | Node.js | MCP Inspector 调试器需要 | `D:\Dev\node` | 调试 MCP 时必须 |
| 6 | Docker Desktop | 跑 MySQL 和 Redis | `D:\Dev\DockerDesktop` | 必须 |
| 7 | DBeaver | 图形化看 MySQL 数据 | 可选安装 | 建议 |
| 8 | 浏览器（Edge/Chrome） | 看 `/docs`、聊天页 | 系统自带 | 必须 |
| 9 | Postman | 测接口（可选，Swagger 已够用） | 可选 | 不必装 |

> 已经在别的盘装了也没关系：本文所有命令都用绝对路径或 `.venv`，不依赖默认安装位置。

## 0.2 软件 1：VS Code

### 步骤 0.1 确认 VS Code 已安装
1. 按 `Win` 键，输入 `Visual Studio Code`。
2. 能搜到并回车打开，就是装好了。
3. 没装的话，浏览器打开 <https://code.visualstudio.com/>，点蓝色 `Download for Windows`，下载后双击安装，安装时勾选：
   - `Add to PATH`
   - `Open with Code` 的右键菜单两项
   - `Register Code as an editor for supported file types`

### 步骤 0.2 装 4 个扩展
1. 打开 VS Code。
2. 按 `Ctrl + Shift + X`，左侧出现「扩展」面板。
3. 在搜索框输入 `Python`，找到 **Python**（作者 Microsoft），点 `Install`。
4. 搜索框改成 `Pylance`，找到 **Pylance**（Microsoft），点 `Install`。
5. 搜索框改成 `DotENV`，找到 **DotENV**，点 `Install`（给 `.env` 上色，防止把 Key 写错行）。
6. 搜索框改成 `Docker`，找到 **Docker**（Microsoft），点 `Install`（在 VS Code 里能看到容器状态）。

✅ 完成标志：扩展面板的「已安装」里有这 4 个。

## 0.3 软件 2：Python + uv

### 步骤 0.3 在终端里确认版本
1. 打开 VS Code。
2. 按 `Ctrl + 反引号(`` ` ``)` 打开集成终端（`反引号` 在 Tab 键上方）。
3. 输入并回车：

```powershell
python -V
```

4. 应该看到 `Python 3.12.10`。
5. 再输入：

```powershell
uv --version
```

6. 应该看到 `uv 0.13.3`（版本号略有差异不影响）。

如果提示 `python 不是内部或外部命令`：在 VS Code 里按 `Ctrl+Shift+P`，输入 `Python: Select Interpreter`，选 `D:\Dev\Python312\python.exe`；或者关掉 VS Code 重开（PATH 是登录时加载的）。

## 0.4 软件 3：Docker Desktop

### 步骤 0.4 确认 Docker 能启动
1. 按 `Win` 键，输入 `Docker Desktop`，回车。
2. 等左下角出现绿色 `Engine running`（首次启动可能要 1–2 分钟）。
3. 回到 VS Code 终端，输入：

```powershell
docker version
```

4. 看到 `Client:` 和 `Server:` 两段都有版本号，就正常。

如果报 `cannot connect to the Docker daemon`：Docker Desktop 还没起完，等 1 分钟再试；还不行就右键任务栏鲸鱼图标 → `Restart`。

## 0.5 软件 4：DBeaver（建议装，不装也能做）

### 步骤 0.5 安装 DBeaver Community
1. 浏览器打开 <https://dbeaver.io/download/>。
2. 下载 `DBeaver Community` 的 Windows 安装包（`.exe`）。
3. 双击安装，一路 `Next`；安装类型选 `For me` 即可。
4. 安装完成后打开，第一次会问是否创建示例数据库，点 `否 / No`。

> 不想装也行：第 3 章会给纯命令行看数据的办法。

✅ 第 0 章完成标志：`python -V`、`uv --version`、`docker version` 三条命令都能正常输出版本。

---

# 第 1 章 先看懂项目（20 分钟）

## 1.1 一句话讲清楚这个项目

员工问问题 → 系统先判断是「制度问题」还是「个人数据问题」：

- **制度问题**（年假怎么算）→ 去 HR 文档里检索 → 大模型基于检索结果回答 → 附上出处。
- **个人数据问题**（我还剩几天年假）→ 大模型调用 MCP 工具 → 工具查 MySQL → 基于查询结果回答。
- **混合问题**（我剩几天年假，离职怎么折算）→ 两条都走。

## 1.2 目录里每个文件是干什么的

| 路径 | 作用 | 你什么时候会打开它 |
|---|---|---|
| `app/config.py` | 读 `.env`，统一配置入口 | 加配置项时 |
| `app/main.py` | FastAPI 服务，`/auth` `/chat` `/search` `/health` | 改接口、看启动流程 |
| `app/auth.py` | users 表校验、PBKDF2 密码哈希、Token 签发 | 改登录逻辑 |
| `scripts/seed_users.py` | 创建 users 表 / 重置密码 | 改演示账号 |
| `app/rag/ingest.py` | 解析文档 → 切分 → 向量化 → 写 Chroma | 加文档、改切分参数 |
| `app/rag/retriever.py` | BM25 + 向量召回 → RRF 融合 → 重排 | 调检索效果 |
| `app/mcp_server/server.py` | MCP Server，4 个只读工具 | 加工具、改权限 |
| `app/mcp_server/db.py` | MySQL 连接 | 改数据库地址 |
| `app/agent/prompts.py` | 路由 / 生成 / 校验的提示词 | 调回答风格 |
| `app/agent/tools.py` | 把 MCP 工具加载成 LangChain 工具 | 改 MCP 启动参数 |
| `app/agent/graph.py` | LangGraph 状态机（核心） | 改流程、调重试 |
| `data/docs/*.md` | 示例 HR 制度文档 | 换成你自己的文档 |
| `data/chunks.jsonl` | 切分结果，BM25 用 | 检查切得好不好 |
| `data/chroma/` | 向量库 | 不用手改 |
| `scripts/seed_db.sql` | 建表 + 插入 3 个员工和 users 账号 | 改测试数据 |
| `scripts/check_env.py` | 环境自检 | 出问题时第一个跑 |
| `scripts/smoke_test.py` | MCP + RAG 冒烟测试 | 改完代码先跑它 |
| `scripts/chat_cli.py` | 命令行测 `/chat` | 测对话 |
| `scripts/download_models_modelscope.py` | 下载 BGE 模型 | 换电脑时 |
| `eval/qa.jsonl` | 50 条评测问题 | 加评测题 |
| `eval/run_eval.py` | 算 Recall@5 / MRR | 调参后跑 |
| `web/index.html` | 浏览器聊天页 | 演示给面试官看 |
| `docker-compose.yml` | MySQL + Redis 定义 | 改端口/密码 |

## 1.3 三条链路（面试必问）

| 问题类型 | 例子 | 走了哪些节点 |
|---|---|---|
| policy 制度 | 年假怎么算？ | `router → retrieve → generate → check` |
| data 个人数据 | 我还剩几天年假？ | `router → agent → tools → agent → generate → check` |
| mixed 混合 | 我剩几天年假，离职怎么折算？ | `router → retrieve → agent → tools → generate → check` |
| chitchat 闲聊 | 你好 | `router → generate` |

## 1.4 两个关键设计（面试加分）

1. **权限不交给模型**：模型只决定「调用哪个工具」，不决定「查哪个员工」。`employee_id` 由服务端注入，MCP Server 里再用 `HR_ALLOWED_IDS` 白名单校验。
2. **答案要校验**：生成后再让模型判断「答案是否被资料支持」，不通过重试一次，仍不通过就明确说「无法确认」，不编造。

✅ 第 1 章完成标志：你能不看文档说出「policy 和 data 分别走哪几个节点」。

---

# 第 2 章 在 VS Code 里打开项目并跑通环境自检

### 步骤 2.1 打开项目文件夹

1. 打开 VS Code。
2. 按 `Ctrl + K`，松开，再按 `Ctrl + O`（或菜单 `File → Open Folder` / 中文界面的「文件 → 打开文件夹」）。
3. 在弹出的窗口地址栏输入：`D:\ClaudeCode\hr-agent`，回车。
4. 点右下角 `Select Folder`（如果弹「是否信任此文件夹的作者」，点 `Yes, I trust the authors`）。
5. 左侧「资源管理器」里应该能看到 `app`、`data`、`scripts` 等文件夹。

### 步骤 2.2 选择 Python 解释器

1. 按 `Ctrl + Shift + P`，上方出现命令面板。
2. 输入 `Python: Select Interpreter`，回车。
3. 列表里选带 `(.venv)` 或路径为 `D:\ClaudeCode\hr-agent\.venv\Scripts\python.exe` 的那一项。
4. 如果列表里没有：点 `Enter interpreter path...` → `Find...` → 手动选 `.venv\Scripts\python.exe`。
5. 看 VS Code 右下角状态栏，应该显示 `3.12.10 ('.venv': venv)`。

> 为什么必须选 `.venv`：项目依赖装在项目自己的虚拟环境里，选错解释器会出现「明明装了包却 import 不到」。

### 步骤 2.3 打开集成终端

1. 按 `Ctrl + 反引号`。
2. 终端出现在下方，提示符类似 `PS D:\ClaudeCode\hr-agent>`。

### 步骤 2.4 激活虚拟环境

1. 在终端输入（注意开头是点和反斜杠）：

```powershell
.\.venv\Scripts\Activate.ps1
```

2. 成功后提示符最前面会出现 `(.venv)`。

如果报红字 `无法加载文件 ... 因为在此系统上禁止运行脚本`：

1. 输入：

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

2. 提示确认时输入 `Y`，回车。
3. 重新执行步骤 2.4 第 1 步。

> 不想改策略也可以不激活，后面所有命令把 `python` 换成 `.\.venv\Scripts\python.exe` 即可。

### 步骤 2.5 设置终端编码（中文不乱码）

每次新开终端执行一次：

```powershell
chcp 65001
$env:PYTHONIOENCODING = "utf-8"
```

> 不改也能跑，但终端里的中文可能变成乱码，影响判断。

### 步骤 2.6 跑环境自检

1. 终端输入：

```powershell
python scripts\check_env.py
```

2. 正常输出长这样（关键看最后几行）：

```text
Python: 3.12.10 ...
== Python 包 ==
  langchain: 1.4.6
  langgraph: 1.2.16
  langchain-mcp-adapters: 0.3.2
  mcp: 1.30.0
  ...
== PyTorch ==
  version: 2.14.1+cpu
  cuda available: False
== MySQL ==
  employees: 3, leave_balances: 3
== Redis ==
  ping: True
  modules: ['bf', 'search', 'timeseries', 'vectorset', 'ReJSON']
== 模型 ==
  embed: OK (2.12 GB) (D:\Dev\models\bge-m3)
  reranker: OK (2.12 GB) (D:\Dev\models\bge-reranker-v2-m3)
```

3. 如果 MySQL 那行报错，说明第 3 章的容器还没起，先继续第 3 章。

✅ 第 2 章完成标志：终端提示符带 `(.venv)`，且 `check_env.py` 能打印 Python 包列表。

---

# 第 3 章 启动 MySQL 和 Redis（Docker Desktop）

## 本章要做什么

项目需要两个「服务」，不用装在本机：

- **MySQL**：存员工、假期余额、考勤。
- **Redis**：存多轮对话的记忆（LangGraph checkpoint）。

Docker 把它们跑成两个容器，一条命令启动。

### 步骤 3.1 启动 Docker Desktop

1. 按 `Win`，输入 `Docker Desktop`，回车。
2. 等窗口左下角变成绿色 `Engine running`。
3. 左侧点 `Containers`，此时列表是空的（还没启动项目容器）。

### 步骤 3.2 在 VS Code 终端启动两个容器

1. 回到 VS Code，确认终端目录是 `D:\ClaudeCode\hr-agent`（提示符里能看到）。
2. 输入：

```powershell
docker compose up -d
```

3. 第一次会拉镜像（几百 MB），等它跑完。成功的输出类似：

```text
[+] Running 4/4
 ✔ Network hr-agent_default  Created
 ✔ Container hr-mysql        Started
 ✔ Container hr-redis        Started
```

4. `-d` 的意思是后台运行，终端不会被占住。

### 步骤 3.3 确认容器健康

1. 输入：

```powershell
docker compose ps
```

2. 看到两行，`STATUS` 列都带 `(healthy)`：

```text
NAME       IMAGE       STATUS
hr-mysql   mysql:8.4   Up (healthy)
hr-redis   redis:8     Up (healthy)
```

3. 如果还是 `starting`，等 20 秒再执行一次。

### 步骤 3.4 在 Docker Desktop 里看容器（可视化确认）

1. 切到 Docker Desktop 窗口。
2. 左侧点 `Containers`。
3. 能看到 `hr-mysql` 和 `hr-redis` 两个条目，左边是绿色。
4. 点 `hr-mysql`，右侧出现 `Logs` 标签，能看到 `ready for connections`。
5. 点右上角方块图标可以 `Stop`，三角形是 `Start`。**现在不要停。**

### 步骤 3.5 用 DBeaver 看数据库（没装 DBeaver 直接跳到 3.6）

1. 打开 DBeaver。
2. 点左上角工具栏的「插头 +」图标（`New Database Connection`）。
3. 列表里选 `MySQL`，点 `Next`。
4. 填：
   - `Server Host`: `127.0.0.1`
   - `Port`: `3306`
   - `Database`: `hr`
   - `Username`: `hr`
   - `Password`: `hr`
5. 点左下角 `Test Connection`。
6. 第一次会弹「下载 MySQL 驱动」，点 `Download`，等进度条走完。
7. 弹出 `Connected` 后点 `OK`，再点 `Finish`。
8. 左侧出现连接 `hr`，展开：`hr → Databases → hr → Tables`。
9. 双击 `employees` 表（或右键 → `View Data`），右侧出现 3 行数据：张三、李四、王五。
10. 同样看 `leave_balances`：张三 `annual_total=10`、`annual_used=3`，所以剩余 7 天。

### 步骤 3.6 不用 DBeaver 时，用命令行看数据

在 VS Code 终端输入（一整行，**不要漏掉 `--default-character-set=utf8mb4`**）：

```powershell
docker exec hr-mysql mysql -uhr -phr --default-character-set=utf8mb4 hr -e "SELECT id,name,department FROM employees;"
```

应该输出：

```text
id    name    department
1001  张三    研发部
1002  李四    产品部
1003  王五    HR 部
```

> 不加 `--default-character-set=utf8mb4` 时，Windows 上的 mysql 客户端可能把中文显示成 `??` 或 `å¼ ä¸‰`。这只影响**显示**，数据本身没坏。
> 验证数据是否真的正常，看十六进制：

```powershell
docker exec hr-mysql mysql -uhr -phr --default-character-set=utf8mb4 hr -e "SELECT name,HEX(name) FROM employees WHERE id=1001;"
```

> 张三对应 `E5BCA0E4B889`。如果这里也不对，才需要第 3.7 步重新导入。

### 步骤 3.7 中文乱码时重新导入种子数据

1. 输入（让 cmd 执行重定向，原始字节直接进容器）：

```powershell
cmd /c "docker exec -i hr-mysql mysql -uroot -proot --default-character-set=utf8mb4 < scripts\seed_db.sql"
```

2. 再执行步骤 3.6 验证，中文应正常。

> 两个坑都别踩：
> - **PowerShell 里直接写 `<`** 会报「`<` 运算符是为将来使用保留的」，所以套一层 `cmd /c`。
> - **不要用 `Get-Content ... | docker exec`**：Windows PowerShell 5.1 读文件默认按 ANSI 解码，UTF-8 的中文会被转坏，导入时直接报 SQL 语法错误（`'???'`）。

### 步骤 3.8 记住三个日常命令

| 场景 | 命令 |
|---|---|
| 启动 | `docker compose up -d` |
| 看状态 | `docker compose ps` |
| 停止（保留数据） | `docker compose stop` |
| 删除容器（数据卷还在） | `docker compose down` |

✅ 第 3 章完成标志：`docker compose ps` 两行都是 `(healthy)`，并且能看到 3 个员工。

---

# 第 4 章 配置 `.env`：填大模型 API Key

## 本章要做什么

项目不把 Key 写死在代码里，而是从项目根目录的 `.env` 读。没有 Key，服务能启动、检索能用，但 `/chat` 会返回 503。

### 步骤 4.1 打开 `.env`

1. 在 VS Code 左侧资源管理器里点 `.env`。
2. 如果看不到（以点开头的文件默认显示，但可能被折叠），按 `Ctrl + P`，输入 `.env`，回车。

### 步骤 4.2 认识每一行

```dotenv
# ===== LLM =====
LLM_PROVIDER=openai                 # openai = 走 OpenAI 兼容接口；anthropic = 走 Claude
LLM_MODEL=deepseek-chat             # 模型名
OPENAI_API_KEY=                     # ← 你要填的就是这里
OPENAI_BASE_URL=https://api.deepseek.com/v1   # 接口地址
```

后面的 `HF_HOME`、`EMBED_MODEL`、`REDIS_URL`、`MYSQL_*`、`HR_ALLOWED_IDS` 都已经配好，**不要改**。

### 步骤 4.3 申请 DeepSeek Key（用 Claude 的话看 4.4）

1. 浏览器打开 <https://platform.deepseek.com/>。
2. 右上角 `登录 / 注册`，用手机号或邮箱注册。
3. 登录后左侧点 `API keys`。
4. 点 `创建 API key`，名字随便填（例如 `hr-agent`），点确定。
5. 弹窗里那串 `sk-` 开头的字符串就是 Key，**只显示一次**，点复制。
6. 左侧点 `充值`，按需充值（跑这个项目调试大约几毛钱到几块钱）。
7. 回到 VS Code，把 Key 粘贴到 `.env` 第 5 行等号后面，不要加引号、不要留空格：

```dotenv
OPENAI_API_KEY=sk-你的真实key
```

8. 按 `Ctrl + S` 保存。

### 步骤 4.4 用 Claude 的话

1. 浏览器打开 <https://console.anthropic.com/>，登录后点 `API Keys` → `Create Key`，复制 `sk-ant-...`。
2. 把 `.env` 前三行改成：

```dotenv
LLM_PROVIDER=anthropic
LLM_MODEL=claude-opus-5-5
ANTHROPIC_API_KEY=sk-ant-你的真实key
```

3. `OPENAI_API_KEY` 留空即可，保存。

### 步骤 4.5 验证 Key 是否被读到

1. 直接运行一次配置检查（不需要起服务）：

```powershell
python -c "from app.config import settings; print(settings.llm_provider, settings.llm_model, settings.llm_configured)"
```

2. 输出应该是 `openai deepseek-chat True`。如果是 `False`，说明 Key 是空的或还带着 `sk-your` 占位符。

> `.env` 已在 `.gitignore` 里，不会被提交。**不要把 Key 发到群里或写进截图。**

✅ 第 4 章完成标志：上面那行打印出 `True`。

---

# 第 5 章 下载本地模型（约 4.3 GB）

## 本章要做什么

两个模型：

- `bge-m3`：把文档和问题变成向量，用来做语义检索。
- `bge-reranker-v2-m3`：把召回的候选重新打分排序。

本机已经在 `D:\Dev\models`，**这一步只是带你验证**；换电脑时才需要重新下载。

### 步骤 5.1 确认模型已在本地

1. 终端输入：

```powershell
dir D:\Dev\models
```

2. 应该看到两个文件夹：`bge-m3`、`bge-reranker-v2-m3`。
3. 再输入：

```powershell
dir D:\Dev\models\bge-m3\pytorch_model.bin
dir D:\Dev\models\bge-reranker-v2-m3\model.safetensors
```

4. 两个文件都应约 `2,271,000,000` 字节（2.1 GB）。

### 步骤 5.2 需要重新下载时（换电脑/文件损坏）

1. 终端输入：

```powershell
python scripts\download_models_modelscope.py
```

2. 屏幕会持续打印进度，类似：

```text
bge-m3 -> D:\Dev\models\bge-m3
  pytorch_model.bin
    pytorch_model.bin: 1024 MB / 2166 MB (47.3%)
```

3. 下载速度约 2–3 MB/s，全程 45–60 分钟，可以最小化窗口去做别的。
4. 结束时会打印：

```text
== 下载完成 ==
  D:\Dev\models\bge-m3: 2.14 GB
  D:\Dev\models\bge-reranker-v2-m3: 2.14 GB
```

5. 中途断了就**重新执行同一条命令**，脚本会从断点续传。

### 步骤 5.3 下载完再跑一次自检

```powershell
python scripts\check_env.py
```

最后两行必须是 `OK (2.12 GB)`。如果显示 `PARTIAL`，说明文件没下完，回到步骤 5.2 重跑。

✅ 第 5 章完成标志：两个模型都显示 `OK`。

---

# 第 6 章 文档入库（RAG 的第一步）

## 本章要做什么

把 `data/docs` 里的 Word/PDF/Markdown 拆成小段，用 `bge-m3` 算成向量，存进 Chroma。之后提问时才能「检索」。

### 步骤 6.1 看有哪些文档

1. VS Code 左侧展开 `data → docs`。
2. 本机有 4 份：
   - `示例-员工手册.md`
   - `示例-假期管理制度.md`
   - `示例-考勤与远程办公制度.md`
   - `示例-薪酬福利与报销制度.md`
3. 双击任意一份，右侧打开，能看到 `# 一、...` 这种标题结构。

> 想换成真实文档：把 `.md` / `.pdf` / `.docx` 放进这个文件夹，重新入库即可。**不要放公司保密文件。**

### 步骤 6.2 执行入库

1. 终端输入：

```powershell
python -m app.rag.ingest
```

2. 等待 1–3 分钟（CPU 算向量较慢），输出：

```text
文档目录：D:\ClaudeCode\hr-agent\data\docs
发现 4 个文件
已生成 48 个 chunk -> D:\ClaudeCode\hr-agent\data\chunks.jsonl
  已写入 32/48
  已写入 48/48
向量库已写入 -> D:\ClaudeCode\hr-agent\data\chroma
```

3. 出现 `向量库已写入` 就是成功。

### 步骤 6.3 检查切分结果

1. 在 VS Code 里按 `Ctrl + P`，输入 `chunks.jsonl`，回车。
2. 文件里每一行是一个 JSON，形如：

```json
{"content":"# 2. 年假天数\n...","metadata":{"source":"示例-假期管理制度.md","heading":"2. 年假天数","chunk_id":"..."}}
```

3. 重点看两点：
   - `content` 是不是一段完整的话，而不是被切在句子中间。
   - `metadata.heading` 是不是有意义的标题，回答时会作为出处显示。

4. 如果一段太长/太碎，去 `app/rag/ingest.py` 改 `chunk_size=500`、`chunk_overlap=80`，再重新跑步骤 6.2。

### 步骤 6.4 什么时候要重新入库

| 情况 | 要不要重跑 `ingest` |
|---|---|
| 新增/修改了 `data/docs` 里的文档 | 要 |
| 改了 `chunk_size` / `chunk_overlap` | 要 |
| 只改了提示词或接口代码 | 不要 |
| 只改了 MySQL 数据 | 不要 |

> 重新入库默认会**清空旧集合**再写，避免重复。想追加用 `python -m app.rag.ingest --no-reset`。

✅ 第 6 章完成标志：看到 `48 个 chunk` 和 `向量库已写入`。

---

# 第 7 章 验证检索效果（RAG 的第二步）

## 7.1 三种验证方式

| 方式 | 需要 LLM Key | 适合什么时候 |
|---|---|---|
| A. 评测脚本 `run_eval.py` | 不需要 | 调参、看整体效果 |
| B. 接口 `/search` | 不需要 | 单条问题快速验证 |
| C. Swagger `/docs` 页面 | 不需要 | 不写代码，点按钮 |

## 方式 A：跑评测（推荐先做）

### 步骤 7.1 执行评测

```powershell
python eval\run_eval.py
```

### 步骤 7.2 看结果

1. 每条问题会打印一行 `HIT/MISS`、命中的排名、Top-1 文档及分数：

```text
[q02] HIT  rank=1  年假没休完可以结转到什么时候？
      top1: 示例-假期管理制度.md (0.9728)
```

2. 最后两行是关键：

```text
Recall@5 = 100.00%  MRR = 0.9714  (35/50 条参与检索评测)
```

3. 指标含义：
   - `Recall@5`：正确答案的文档有没有出现在前 5 条里。100% = 全部命中。
   - `MRR`：正确答案排得有多靠前，越接近 1 越好。
   - 只有 35 条参与，是因为另外 10 条是数据类（走 MCP，不检索）、5 条是不可回答题。

### 步骤 7.3 保存结果

```powershell
python eval\run_eval.py --output "D:\ClaudeCode\数据\2026-10-22-检索评测.json"
```

> 建议每次调完参数存一份，面试时能拿出「参数对比」的证据。

## 方式 B：调 `/search` 接口

先启动服务：

### 步骤 7.4 启动 API

1. 新开一个终端（VS Code 里点终端面板右上角的 `+`）。
2. 输入：

```powershell
python -m app.main
```

3. 看到 `Uvicorn running on http://127.0.0.1:8000` 就是起来了。**这个终端不要关**，它就是这个服务。
4. 第一个终端保留给其他命令。

### 步骤 7.5 发一条检索请求

在**另一个**终端输入：

```powershell
python scripts\search_cli.py "年假没休完可以结转到什么时候"
```

预期输出：

```text
200
0.9728 示例-假期管理制度.md | 3. 年假使用与结转
0.2032 示例-假期管理制度.md | 4. 年假工资与离职折算
0.137 示例-假期管理制度.md | 8. 产假、陪产假与育儿假
```

> 第一条分数 0.97 远高于后面，说明重排得很干净。如果第一条分数也很低（<0.3），说明这个问题文档里确实没有。

## 方式 C：用 Swagger 页面点按钮

### 步骤 7.6 打开接口文档

1. 浏览器打开 <http://127.0.0.1:8000/docs>。
2. 页面列出 `GET /`、`GET /health`、`POST /auth/login`、`GET /auth/me`、`POST /search`、`POST /chat`。

### 步骤 7.7 点按钮测 `/search`

1. 点 `POST /search` 这一行，展开。
2. 点右上角 `Try it out`。
3. 在 `Request body` 的输入框里改成：

```json
{
  "query": "迟到30分钟以内怎么处理",
  "top_k": 3
}
```

4. 点蓝色 `Execute`。
5. 往下看 `Response body`，应该是 200 和三条结果，第一条来自 `示例-考勤与远程办公制度.md`。

## 7.8 检索效果不好怎么排查

| 现象 | 先查什么 | 怎么改 |
|---|---|---|
| 返回结果为空 | `data/chunks.jsonl` 是否存在且非空 | 重跑入库 |
| 命中了错误文档 | 文档里有没有同义但不同的说法 | 加同义词、调 chunk_size |
| 分数普遍很低 | 问题是否超出文档范围 | 正常，应该走拒答 |
| 第一条不是想要的 | 重排模型没加载 | 看启动日志有没有 reranker 报错 |

✅ 第 7 章完成标志：`Recall@5` 能看到数字，`/search` 返回三条带 `source` 的结果。

---

# 第 8 章 验证 MCP Server

## 8.1 MCP 到底是什么（一分钟版）

- 普通「函数调用」：你把函数写在应用里，模型输出「调这个函数」。
- **MCP**：工具独立成一个**进程/服务**，通过标准协议暴露给任何客户端（Claude Desktop、IDE、你的 Agent）。
- 好处：工具可复用、可单独测试、可加权限和审计、换语言也不用改 Agent。

本项目的 MCP Server 暴露 **4 个只读工具**：

| 工具 | 参数 | 作用 |
|---|---|---|
| `get_leave_balance` | `employee_id` | 年假/病假总额与剩余 |
| `get_attendance` | `employee_id`, `month`（`YYYY-MM`） | 某月考勤汇总与明细 |
| `get_employee_profile` | `employee_id` | 部门、邮箱、直属上级 |
| `get_org_info` | `name` | 按姓名查组织信息 |

### 步骤 8.1 用脚本一次性验证（最稳）

1. 终端输入：

```powershell
python scripts\smoke_test.py
```

2. 预期输出：

```text
== MCP 工具 ==
  PASS get_leave_balance {'employee_id': 1001}
  PASS get_attendance {'employee_id': 1001, 'month': '2026-10'}
  PASS get_employee_profile {'employee_id': 1001}
  PASS get_org_info {'name': '张三'}
  PASS get_leave_balance {'employee_id': 9999}
== RAG 检索 ==
  1. 示例-假期管理制度.md / 3. 年假使用与结转  score=0.9728
  PASS 命中示例-假期管理制度.md
```

3. 第 5 个 `PASS` 是**故意用越权工号 9999**，预期返回「无权限」。如果它返回了数据，说明权限逻辑坏了。

### 步骤 8.2 用 MCP Inspector 手动点（面试可演示）

1. 确认 Node 可用：

```powershell
node -v
```

应该输出 `v24.x`。

2. 终端输入（注意 `mcp.exe` 是虚拟环境里的）：

```powershell
.\.venv\Scripts\mcp.exe dev app\mcp_server\server.py
```

> 不需要再设置 `PYTHONPATH`。[server.py](app/mcp_server/server.py) 开头已经把项目根目录加入了 `sys.path`，所以 `mcp dev` 和它内部调用的 `mcp run` 都能直接找到 `app` 包。
> 如果仍然报 `ModuleNotFoundError: No module named 'app'`，说明运行的是没有这段引导的旧代码：检查 `server.py` 开头是否有 `_PROJECT_ROOT` 那几行，或者直接改用第 5 步的 `python -m` 方式启动。

3. 第一次会自动下载 Inspector，等待 30–60 秒。
4. 浏览器自动打开 `http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...`。
5. 页面左侧 `Transport Type` 保持 `STDIO`。**不要直接用默认的 `uv run ...`**，把它改成：
   - `Command`：`D:\ClaudeCode\hr-agent\.venv\Scripts\python.exe`
   - `Arguments`：`-m app.mcp_server.server`
   - `Working Directory`（有这一栏就填）：`D:\ClaudeCode\hr-agent`

   然后点 `Connect`。
   如果保留默认的 `uv` 命令，理论上也能直接连上；如果提示 `Failed to connect to "uv"` 或缺少 `pymysql`，再改用上面的 `python.exe -m app.mcp_server.server`。
6. 连接成功后，点顶部 `Tools` 标签。
7. 点 `List Tools`，右侧出现 4 个工具卡片。
8. 点 `get_leave_balance`，参数框填 `1001`，点 `Run Tool`。
9. 下方 `Result` 里能看到 `annual_remaining: 7`。
10. 换成 `9999` 再跑一次，应该看到权限错误 —— 这就是演示「服务端鉴权」的最好画面。

> 如果 `mcp dev` 启动失败（版本差异），用 `npx -y @modelcontextprotocol/inspector` 也能达到同样效果；或者直接用步骤 8.1 的脚本，效果一样。
> Inspector 会记住上次的 `Command` / `Arguments`，第二次打开通常不用再改。
> 关掉 Inspector：在终端按 `Ctrl + C`。

### 步骤 8.3 看审计日志

1. 用终端查看（`logs/` 在 `.gitignore` 里，VS Code 的 `Ctrl + P` 默认会跳过被忽略的目录，可能搜不到）：

```powershell
Get-Content logs\mcp_audit.jsonl -Tail 10
```

也可以直接打开：在终端执行 `code logs\mcp_audit.jsonl`，或在 VS Code 里按 `Ctrl+O` 粘贴完整路径。

2. 每行是一条调用记录，成功和失败都会写：

```json
{"ts": "2026-10-24T13:56:55.645948+00:00", "tool": "get_leave_balance", "employee_id": 1002, "params": {"employee_id": 1002}, "ok": true}
{"ts": "2026-10-24T12:51:45.965512+00:00", "tool": "get_leave_balance", "employee_id": 9999, "params": {"employee_id": 9999}, "ok": false, "error": "没有权限查询员工 9999 的数据"}
```

3. 面试时说：「每次工具调用都有审计，出问题能追到是谁、查了什么、成功没有。」

## 8.4 MCP 常见错误

| 报错 | 原因 | 处理 |
|---|---|---|
| `Processing request of type CallToolRequest` 刷屏 | 这是正常日志 | 忽略 |
| `employee 9999 is not allowed` | 白名单生效 | 正常，就是要这个效果 |
| `Can't connect to MySQL` | 容器没起 | 回第 3 章 |
| `No module named app` | 运行的 `server.py` 没有内置 `sys.path` 引导，或改的是另一份副本 | 确认 `server.py` 开头有 `_PROJECT_ROOT` 引导；临时可执行 `$env:PYTHONPATH = "D:\ClaudeCode\hr-agent"` 后重启 |
| 中文乱码 | 控制台编码 | `chcp 65001` |

✅ 第 8 章完成标志：`smoke_test.py` 显示 6 个 PASS。

---

# 第 9 章 启动 API，做一次完整对话

## 服务启动后的三个地址

| 地址 | 作用 |
|---|---|
| <http://127.0.0.1:8000/health> | 健康检查（最重要） |
| <http://127.0.0.1:8000/docs> | Swagger，可以点按钮调接口 |
| <http://127.0.0.1:8000/ui/> | 浏览器聊天页（先登录） |
| `POST /auth/login` | 工号密码登录，换取 Token |
| `POST /chat` | 流式对话（SSE，需要 Bearer Token） |

### 步骤 9.1 确认服务在跑

1. 第 7 章启动的终端如果还在，直接下一步；关了就重新执行：

```powershell
python -m app.main
```

> 如果 `python` 不是项目 `.venv` 里的解释器，改用 `.\.venv\Scripts\python.exe -m app.main`。
> 启动时要加载 BGE 模型和 MCP 子进程，通常需要 **15–30 秒**。等终端出现 `Application startup complete` 和 `Uvicorn running on http://127.0.0.1:8000` 后再打开链接；提前打开会显示「无法访问此网站 / 拒绝连接」。

2. 浏览器打开 <http://127.0.0.1:8000/health>（必须是 `http`，不要用 `https`；地址用 `127.0.0.1`，不要用 `0.0.0.0`）。
3. 填好 Key 后应该看到：

```json
{
  "status": "ok",
  "llm_provider": "openai",
  "llm_model": "deepseek-chat",
  "llm_configured": true,
  "graph_ready": true,
  "checkpointer": "redis",
  "chunks": 48,
  "tools": ["get_leave_balance", "get_attendance", "get_employee_profile", "get_org_info"],
  "startup_error": null
}
```

4. 逐项看：
   - `llm_configured` 必须 `true` —— 否则回第 4 章。
   - `graph_ready` 必须 `true` —— 否则看 `startup_error` 写的原因。
   - `checkpointer` 是 `redis` —— 说明会话记忆持久化生效；如果是 `memory`，说明 Redis 没连上。
   - `chunks` 是 `48` —— 说明检索器加载了入库结果。
   - `tools` 有 4 个 —— 说明 MCP 子进程启动成功。

> 改了 `.env` 必须**重启服务**（终端 `Ctrl+C`，再 `python -m app.main`），配置不是热加载的。

### 步骤 9.2 用命令行测一次对话

1. 新开一个终端。
2. 输入：

```powershell
python scripts\chat_cli.py "我还有几天年假？"
```

> 脚本会先用 `1001 / 123456` 调 `/auth/login` 拿 Token，再请求 `/chat`；可用 `--employee`、`--password`、`--token` 覆盖。
> 账号密码存在 MySQL `users` 表，密码是 PBKDF2 哈希。已有数据库执行 `python scripts\seed_users.py` 初始化；重置密码用 `python scripts\seed_users.py --ids 1001 --password 新密码 --reset`。

3. 预期输出（逐字流式打印）：

```text
回答：你目前年假总额 10 天，已使用 3 天，还剩 7 天。

[route=data grounded=True retry=0]
```

> 如果只输出 `[错误] 对话失败，请查看服务端日志后重试`，去跑服务的那个终端看最后一段 Traceback。最常见的是：
> `openai.AuthenticationError: Error code: 401 ... 令牌已过期或验证不正确`
> 说明 `.env` 里的 `OPENAI_API_KEY` 无效。智谱 BigModel 的 Key 是 `id.secret` 两段、中间有一个英文句点（共 60 多字符）；只复制前 32 位也会报 401。换完整 Key 后**必须重启服务**。

4. 再问一个制度问题：

```powershell
python scripts\chat_cli.py "年假没休完可以结转到什么时候？" --session demo-1
```

5. 预期回答包含「次年 3 月 31 日」之类的制度原文，并在 `[来源]` 里列出 `示例-假期管理制度.md`。

### 步骤 9.3 测多轮记忆

同一个 `--session` 连续问：

```powershell
python scripts\chat_cli.py "我还有几天年假？" --session demo-2
python scripts\chat_cli.py "那病假呢？" --session demo-2
```

第二个问题里的「那」能接上，说明 Redis checkpoint 生效。换个 `--session demo-3` 再问「那病假呢」，它应该不知道你在问谁。

> 记忆是按会话隔离的，一个员工一个会话，这也是真实系统的做法。

### 步骤 9.4 在 Swagger 里测（注意 SSE）

1. 打开 <http://127.0.0.1:8000/docs>。
2. 展开 `POST /auth/login` → `Try it out`，请求体填：

```json
{
  "employee_id": 1001,
  "password": "123456"
}
```

3. 点 `Execute`，复制返回的 `access_token`。
4. 点页面右上角 `Authorize`，粘贴 Token（不要加 `Bearer ` 前缀），确认。
5. 展开 `POST /chat` → `Try it out`，请求体填：

```json
{
  "message": "我上个月迟到几次？",
  "session_id": "demo-1"
}
```

6. 点 `Execute`。
7. Swagger 会把整个 SSE 流一次性显示出来，能看到 `event: meta`、多条 `event: token`、最后 `event: done`。
8. 注意 `done` 里同时带了完整 `answer`、`route`、`grounded`、`sources`。

### 步骤 9.5 用浏览器聊天页（演示用）

1. 确认后端已启动。
2. 浏览器打开 <http://127.0.0.1:8000/ui/>（或直接双击 `web\index.html`）。
3. 用演示账号登录：工号 `1001`，密码 `123456`。也可以用 `1002` / `1003`。
4. 在底部输入「我还有几天年假？」，点发送。
5. 回答会**逐字出现**，下面显示 `route=data · grounded=True · retry=0`。
6. 再输入「年假没休完可以结转到什么时候？」，看来源是否正确。
7. 侧边栏底部可以退出登录。

> 登录成功后 Token 保存在浏览器本地，刷新页面不需要重复登录；退出登录会清除 Token。聊天记录按工号分开保存。

## 9.6 SSE 事件速查

| 事件 | 含义 | 前端要做什么 |
|---|---|---|
| `meta` | 会话和工号确认 | 可忽略 |
| `token` | 一个字/词 | 追加到气泡 |
| `reset` | 事实校验没过，重新生成 | **清空当前气泡** |
| `done` | 结束，带完整答案和来源 | 用 `answer` 兜底覆盖 |
| `error` | 服务端异常 | 提示重试 |

## 9.7 关掉服务

在运行服务的终端按 `Ctrl + C`。

✅ 第 9 章完成标志：`/health` 里 `graph_ready=true`，且能问出「还剩 7 天年假」。

---

# 第 10 章 在 VS Code 里断点调试（面试前一定要会）

### 步骤 10.1 创建调试配置

1. VS Code 左侧点「运行和调试」图标（三角形 + 虫子，或按 `Ctrl + Shift + D`）。
2. 点蓝色字 `create a launch.json file`。
3. 弹出的选择框里选 `Python Debugger`，再选 `FastAPI`（没有就选 `Python File`）。
4. VS Code 自动生成 `.vscode\launch.json`。
5. 把内容改成下面这份（直接覆盖）：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "HR Agent API",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--host", "127.0.0.1", "--port", "8000"],
      "cwd": "${workspaceFolder}",
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal",
      "justMyCode": true
    },
    {
      "name": "环境自检",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/scripts/check_env.py",
      "cwd": "${workspaceFolder}",
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ]
}
```

6. 按 `Ctrl + S` 保存。

### 步骤 10.2 下断点

1. 打开 `app/agent/graph.py`。
2. 找到 `async def router_node(state: AgentState)`（约第 145 行）。
3. **断点点在函数体第一行**，也就是它下面的 `question = _last_user_text(state["messages"])`，不要点在 `async def` 那一行。
4. 同样在 `async def generate_node(...)`（约第 204 行）下面的 `messages = list(state["messages"])` 点一个。

> 为什么不能点在 `async def` 行：那行只在启动时构建图执行一次，此时还没有任何请求，`state` 也不存在。断在那里后，变量面板和监视表达式都会报 `NameError: name 'state' is not defined`。

> 其它可用断点：`retrieve_node`（约 166 行，看召回了几条）、`agent_node`（约 188 行，看有没有产生 tool_calls）、`check_node`（约 234 行，看 grounded 判断）。

### 步骤 10.3 启动调试

1. 按 `F5`。
2. 顶部出现调试工具条：继续（▶）、单步跳过（⤵）、单步进入（⤓）、重启、停止。
3. 看到 `Uvicorn running` 说明服务在调试模式下启动。

### 步骤 10.4 触发断点

1. 用另一个终端执行：

```powershell
python scripts\chat_cli.py "年假没休完可以结转到什么时候？"
```

2. VS Code 窗口自动跳到断点处，那一行变黄。

### 步骤 10.5 看变量

1. 左侧 `变量 / VARIABLES` 面板展开 `state`，能看到 `messages`、`employee_id`、`route`、`context`。
2. 在 `监视 / WATCH` 面板点 `+`，输入 `state["messages"][-1].content`，能看到当前问题原文。
3. 按 `F10`（单步跳过）一行行往下走，按 `F5`（继续）跑到下一个断点。
4. 看完在工具条点红色方块停止，或者 `Shift + F5`。

> 如果监视窗口报 `NameError: name 'state' is not defined`，先看左侧 `调用堆栈 / CALL STACK`：应该停在 `router_node` 或 `generate_node` 这一帧。如果顶上是 `build_graph` 或 `asyncio` 内部帧，说明断点打在 `async def` 行或停在了别的调用里——点一下 `CALL STACK` 里的 `router_node` 帧，或者在函数体第一行重新下断点。变量和监视表达式都是按**当前选中的栈帧**求值的。

### 步骤 10.6 调试 MCP 子进程（进阶）

MCP Server 是 Agent 用 `python -m app.mcp_server.server` **另起的一个进程**，主调试器默认进不去。两种办法：

1. **加日志**：在 `app/mcp_server/server.py` 的工具函数里 `print(..., file=sys.stderr)`，日志会出现在 API 终端里。
2. **单独调试**：在 `launch.json` 再加一个配置，`"program"` 指向 `app/mcp_server/server.py`，先启动它，再从 Inspector 连。

✅ 第 10 章完成标志：F5 能起服务，请求能在断点处停下来，能看到 `state` 里的变量。

---

# 第 11 章 改造练习（面试时讲「我做了什么」）

> 面试官最怕听到「照教程抄的」。下面 4 个练习，做一个就够讲 10 分钟。

## 练习 1：加一个 MCP 工具 `get_pending_leaves`

**目标**：查某员工待审批的请假单，让 Agent 能回答「我提交的请假批了吗」。

### 步骤 11.1 建表并插数据
1. 打开 `scripts/seed_db.sql`。
2. 在文件末尾加：

```sql
CREATE TABLE IF NOT EXISTS leave_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  employee_id INT NOT NULL,
  leave_type VARCHAR(20) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending'
);

INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, status) VALUES
  (1001, 'annual', '2026-11-02', '2026-11-03', 'pending'),
  (1001, 'sick',   '2026-09-15', '2026-09-16', 'approved')
ON DUPLICATE KEY UPDATE status = VALUES(status);
```

3. 重新导入（注意 `-i`，以及 PowerShell 不支持 `<`）：

```powershell
cd D:\ClaudeCode\hr-agent
cmd /c "docker exec -i hr-mysql mysql -uroot -proot --default-character-set=utf8mb4 < scripts\seed_db.sql"
```

> PowerShell 里 `<` 是保留运算符，直接写会报 `“<”运算符是为将来使用而保留的`，必须套一层 `cmd /c`。
> 如果你用的是 Git Bash 终端（VS Code 右下角可以切换），可以直接写：
> `docker exec -i hr-mysql mysql -uroot -proot --default-character-set=utf8mb4 < scripts/seed_db.sql`
> 不要用 `Get-Content | docker exec`，PowerShell 5.1 会把 UTF-8 中文转坏。

4. 验证：

```powershell
docker exec hr-mysql mysql -uhr -phr --default-character-set=utf8mb4 hr -e "SELECT * FROM leave_requests;"
```

### 步骤 11.2 加工具函数
1. 打开 `app/mcp_server/server.py`。
2. 找到最后一个 `@mcp.tool()` 函数之后的位置，追加：

```python
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
```

> 三个要点（照着已有工具抄就不会错）：
> 1. `cursor()` 是从 `app.mcp_server.db` 导入的上下文管理器，直接 `with cursor() as cur:`，**不要自己建连接**。
> 2. `_audit(tool, employee_id, params, ok, error)` 是现成的，成功失败都要记。
> 3. 返回统一 `{"ok": True, "data": ...}` 或 `{"ok": False, "error": ...}`，Agent 才好判断。
>
> `date` 类型不能直接 JSON 序列化，所以上面把 `start_date` / `end_date` 转成了字符串。

### 步骤 11.3 验证
1. 重启 API（`Ctrl+C` 后 `python -m app.main`）。
2. 跑：

```powershell
python scripts\chat_cli.py "我提交的请假批了吗？"
```

3. 预期：`route=data`，回答提到 1 条待审批的年假（11 月 2–3 日）。
4. 如果模型不调用新工具：检查 docstring 有没有写「什么时候用」，这是模型选工具的主要依据。

## 练习 2：让回答带上「文档标题 + 页码」

**目标**：现在引用是 `[来源: 文件名 / 标题]`，改成更完整的格式，面试时更好看。

1. 打开 `app/rag/retriever.py`。
2. 找到 `format_context`，把 `f"[资料{index}] 来源：{item.source} / {item.heading}"` 改成：

```python
f"[资料{index}] 来源：《{item.source}》· {item.heading}"
```

3. 打开 `app/agent/prompts.py`，把要求引用格式的那一句同步改成 `[来源: 《文件名》· 标题]`。
4. 重启服务，问一个制度问题，看回答里的引用格式。

> 这个改动很小，但能讲「引用格式为什么要跟产品走」——面试官会认为你想过可用性。

## 练习 3：让 retry 按链路分流

**目标**：现在校验失败后统一回 `generate` 重新生成。但 data 类问题缺的是「工具查回来的数据」，光重写答案没用，应该回 `agent` 重新调工具。

1. 打开 `app/agent/graph.py`。
2. 按 `Ctrl + F` 搜 `route_after_check`，找到这个函数：

```python
def route_after_check(state: AgentState) -> str:
    if state.get("grounded"):
        return END
    if state.get("retry_count", 0) <= 1:
        return "generate"
    return "fallback"
```

3. 把中间那两行改成：

```python
    if state.get("retry_count", 0) <= 1:
        return "agent" if state.get("route") in {"data", "mixed"} else "generate"
```

4. 往下找 `add_conditional_edges("check", ...)`，把映射改成：

```python
    graph.add_conditional_edges(
        "check",
        route_after_check,
        {"generate": "generate", "agent": "agent", "fallback": "fallback", END: END},
    )
```

5. 重启服务，问一个 data 类问题；再故意把 `.env` 的 `HR_ALLOWED_IDS` 改成 `1002` 让工具受限，观察重试路径。

> 面试点：「check 失败要回到产生答案的那条链路 —— 缺资料回检索、缺数据回工具，而不是无条件重写答案。」
> 注意 `agent → generate → check → agent` 是有环的，靠 `retry_count <= 1` 兜住，不会死循环。

## 练习 4：加一个「答案缓存」

**目标**：同一个问题重复问，直接命中缓存，P95 延迟下降。

1. 在 `app/main.py` 顶部加：

```python
import hashlib
from app.config import settings
import redis.asyncio as aioredis
```

2. 在 `lifespan` 里初始化：`app.state.cache = aioredis.from_url(settings.redis_url, decode_responses=True)`。
3. 在 `/chat` 里，生成前先查：

```python
key = "hr:answer:" + hashlib.md5(f"{payload.message}".encode()).hexdigest()
cached = await app.state.cache.get(key)
```

4. 命中就直接返回一条 `done` 事件；没命中就正常走，结束后 `setex(key, 600, answer)`。
5. 注意：**只缓存 policy 类**，data 类不能缓存（数据会变）。

> 这个练习能讲「缓存边界」：什么能缓存、什么绝对不能，是工程判断力。

✅ 第 11 章完成标志：至少完成练习 1，并能说清楚改动了哪几个文件。

---

# 第 12 章 评测与调参

## 12.1 四个指标

| 指标 | 怎么算 | 现在是多少 |
|---|---|---|
| Recall@5 | 正确文档在前 5 条的比例 | 100% |
| MRR | 正确文档排名的倒数平均 | 0.9714 |
| 工具调用准确率 | data 类问题是否调对工具 | 需要接 LLM 后人工看 |
| 拒答率 | 不可回答题是否明确说「无法确认」 | 需要接 LLM 后人工看 |

### 步骤 12.2 做一次参数对比实验

1. 记录当前基线：`python eval\run_eval.py --output D:\ClaudeCode\数据\2026-10-22-基线.json`。
2. 改 `.env` 里的 `RETRIEVAL_RECALL_K=20`。
3. 重启服务（如果开着）。
4. 再跑：`python eval\run_eval.py --output D:\ClaudeCode\数据\2026-10-22-候选20.json`。
5. 对比两次的 Recall@5 和单次检索耗时。
6. 本机实测：20 个候选 17–22 秒，10 个候选 6–11 秒，指标完全一样 —— 这就是「默认取 10」的依据。

> 面试时这句比任何形容词都有说服力：「我用 20 和 10 做了对比，Recall@5 都是 100%，但延迟从 17 秒降到 6 秒，所以选了 10。」

### 步骤 12.3 换 chunk_size 再测

1. 打开 `app/rag/ingest.py`，把 `chunk_size=500` 改成 `300`。
2. 重新入库：`python -m app.rag.ingest`。
3. 跑评测。
4. 把结果记到表里，再改回 `500` 重新入库。

| chunk_size | overlap | recall@5 | 备注 |
|---|---|---|---|
| 300 | 80 | （你跑出来的） | |
| 500 | 80 | 100% | 当前 |
| 800 | 120 | （你跑出来的） | |

> 不要编数字。跑出来多少写多少，面试官问「为什么 500」时你就有话可说。

## 12.4 接 LLM 之后要补的评测

检索指标只覆盖 policy 类。接上 Key 后，还要人工跑这 10 条 data 类问题，记录「有没有调对工具、参数对不对」：

```powershell
python scripts\chat_cli.py "我还有几天年假？"
python scripts\chat_cli.py "我上个月迟到几次？"
python scripts\chat_cli.py "我这个月有几天正常出勤？"
python scripts\chat_cli.py "我的部门是什么？"
python scripts\chat_cli.py "我的直属上级是谁？"
python scripts\chat_cli.py "李四还有几天年假？"
python scripts\chat_cli.py "王五的病假还剩几天？"
python scripts\chat_cli.py "张三2026年10月的考勤汇总是什么？"
python scripts\chat_cli.py "李四的邮箱是什么？"
python scripts\chat_cli.py "王五属于哪个部门？"
```

再跑 5 条应该拒答的：

```powershell
python scripts\chat_cli.py "公司食堂几点开饭？"
python scripts\chat_cli.py "公司有班车吗？"
python scripts\chat_cli.py "员工可以带宠物上班吗？"
python scripts\chat_cli.py "公司股票代码是多少？"
python scripts\chat_cli.py "今年的年终奖是多少？"
```

✅ 第 12 章完成标志：你能拿出至少一张自己跑出来的参数对比表。

---

# 第 13 章 三天排期（每格都是可验收的）

## Day 1：环境 + 数据 + 检索（约 3 小时）

- [ ] 第 0 章：三条版本命令通过
- [ ] 第 2 章：`.venv` 激活 + `check_env.py` 打印包列表
- [ ] 第 3 章：`docker compose ps` 两个 healthy
- [ ] 第 4 章：`llm_configured` 打印 `True`
- [ ] 第 6 章：入库出 `48 个 chunk`
- [ ] 第 7 章：`Recall@5` 跑出数字，`/search` 返回三条

## Day 2：MCP + LangGraph（约 3 小时）

- [ ] 第 8 章：`smoke_test.py` 6 个 PASS
- [ ] 第 9 章：`/health` 里 `graph_ready=true`
- [ ] 第 9 章：`chat_cli.py` 问出「还剩 7 天年假」
- [ ] 第 9 章：同 session 追问「那病假呢」能接上
- [ ] 第 10 章：能在 `router` 断点停住并看到 `state`

## Day 3：改造 + 评测 + 演示（约 3 小时）

- [ ] 第 11 章：完成练习 1（加工具）或练习 3（retry 分流）
- [ ] 第 12 章：跑一张参数对比表
- [ ] 第 9 章：浏览器聊天页能演示
- [ ] 第 14 章：按话术讲 3 遍（录音回放一遍）
- [ ] 可选：把项目推到 GitHub（`.env`、`data/chroma` 不要提交）

---

# 第 14 章 报错速查

| 你看到的现象 | 最可能的原因 | 具体怎么做 |
|---|---|---|
| `python 不是内部或外部命令` | PATH 没加载 | 重开 VS Code；或 `Ctrl+Shift+P` 选解释器 |
| `ModuleNotFoundError: No module named 'app'` | 终端不在项目根目录 | `cd D:\ClaudeCode\hr-agent` |
| `ModuleNotFoundError: langchain...` | 没选对解释器 | 步骤 2.2 |
| `Activate.ps1 无法加载` | 执行策略 | 步骤 2.4 的 `Set-ExecutionPolicy` |
| 终端中文乱码 | 编码 | `chcp 65001` + `$env:PYTHONIOENCODING="utf-8"` |
| `docker: command not found` | Docker 没起或 PATH | 打开 Docker Desktop；重开终端 |
| `port 3306 is already allocated` | 本机装了 MySQL | `net stop MySQL80`，或改 compose 端口 |
| MySQL 显示 `å¼ ä¸‰` | 客户端编码 | 步骤 3.7 用 `--default-character-set=utf8mb4` 重导 |
| `check_env.py` 里 MySQL 报错 | 容器没起 | 第 3 章 |
| 模型显示 `PARTIAL` | 权重没下完 | 重跑下载脚本（会续传） |
| `/chat` 返回 503 | Key 没填 / graph 没起来 | 看 `/health` 的 `startup_error` |
| `/chat` 返回 403 | 工号不在白名单 | 用 1001/1002/1003，或改 `.env` 的 `HR_ALLOWED_IDS` |
| 第一次检索 20 秒 | 模型在加载 | 正常，第二次开始 6–11 秒 |
| 回答不带来源 | 模型没按格式 | 检查 `prompts.py` 的引用要求 |
| Agent 不调工具 | docstring 没写清用途 | 在工具函数 docstring 里写「什么时候用」 |
| 回答「无法确认」但文档里有 | 召回没命中 | 跑 `/search` 看检索结果 |
| 改了 `.env` 没生效 | 配置不热加载 | `Ctrl+C` 重启服务 |
| `mcp dev` 起不来 | 版本/网络 | 用 `smoke_test.py` 代替 |
| Inspector 连不上 | 端口 6274 被占 | 关掉旧进程，或换端口 |

---

# 第 15 章 面试怎么讲

## 15.1 60 秒项目介绍

> 这是一个面向企业 HR 场景的问答 Agent，员工可以问两类问题：制度问题和个人数据问题。
>
> 制度问题走 RAG：我先用 PyMuPDF 和 python-docx 解析文档，按标题层级切 section，再用递归字符切分，每块 500 token、重叠 80；用本地 BGE-M3 做 Embedding 存到 Chroma。检索时向量和 BM25 各召回，用 RRF 融合，再用 bge-reranker 重排取 Top-5，回答会带文档出处。
>
> 个人数据走 MCP：我把假期余额、考勤、员工档案、组织信息封装成 4 个只读 MCP 工具，服务端做工号白名单和审计日志，员工 ID 不从模型来。
>
> 整个流程用 LangGraph 编排：router 先判断问题类型，再分别走 retrieve 或 agent/tools，生成后有一个 check 节点校验答案有没有依据，不通过重试一次，仍不通过就明确兜底。
>
> 我自建了 50 条评测集，检索 Recall@5 是 100%，MRR 0.97；实测把重排候选从 20 降到 10，指标不变而单次检索从 17 秒降到 6 秒。

## 15.2 高频追问与回答

**Q：为什么 chunk size 选 500？**
> 制度条款通常 200–800 字，500 token 能保住一条完整规则；太小上下文断裂，太大召回不精准。我用 300/500/800 做过对比，500 的 Recall@5 最好（说你自己跑出来的数字）。

**Q：为什么要 BM25 + 向量？**
> 向量擅长语义相近，但「第 12 条」这种精确词容易漏；BM25 擅长关键词精确匹配。两路召回后用 RRF 融合，RRF 只看排名，不依赖两路分数的量纲。

**Q：为什么要 rerank？**
> 召回阶段追求 recall，Top-20 里有噪声；cross-encoder 把 query 和 chunk 一起编码，排序更准但慢，所以只对少量候选重排。

**Q：怎么防幻觉？**
> 四层：检索结果带出处；prompt 只允许依据 context；生成后 check 节点做 groundedness 校验；没依据走 fallback 明确拒答。

**Q：MCP 和 function calling 有什么区别？**
> function calling 是模型输出「要调用某个函数」的机制；MCP 是标准化的 Client/Server 协议，统一了工具的发现、传输和权限。同一个 MCP Server 可以被 Claude Desktop、IDE、你的 Agent 复用，不用为每个宿主重写。

**Q：为什么用 LangGraph，不用 Dify？**
> Dify 适合快速搭固定流程；LangGraph 是代码级 StateGraph，适合有状态、条件路由、循环重试、需要单测和版本管理的场景。这个项目 router、retrieve、agent、generate、check 本身就是个有环状态机。

**Q：员工权限怎么控制？**
> 员工 ID 从登录态注入而不是模型传入；MCP Server 内做白名单和行级校验；数据库用只读账号；每次调用写审计日志。

**Q：延迟怎么优化？**
> 三个手段：重排候选从 20 降到 10；chunk 控制在 500 token 内避免超长输入；答案缓存（policy 类可缓存，data 类不可）。

**Q：文档里有表格/扫描件怎么办？**
> 表格用 PyMuPDF 的 table 提取转 Markdown 再切；扫描件先 OCR（PaddleOCR）再走同样的入库流程。

## 15.3 不要说的话

- 不要说「用了向量库所以不会幻觉」。
- 不要说「LangGraph 比 Dify 高级」。
- 不要编召回率、准确率、延迟数字。
- 不要说「MCP 就是 function calling 换了个名字」。

---

# 附录 A：换台电脑从零重建（命令清单）

```powershell
# 1. 装 Python 3.12 / uv / Git / Node / Docker Desktop（装到 D 盘）
# 2. 建项目
mkdir D:\ClaudeCode\hr-agent
cd D:\ClaudeCode\hr-agent

# 3. 放代码后建虚拟环境
D:\Dev\Python312\Scripts\uv.exe sync

# 4. 起数据库
docker compose up -d

# 5. 配 .env（复制 .env.example 后填 Key）
copy .env.example .env

# 6. 下载模型（约 45 分钟）
.\.venv\Scripts\python.exe scripts\download_models_modelscope.py

# 7. 入库 + 自检
.\.venv\Scripts\python.exe -m app.rag.ingest
.\.venv\Scripts\python.exe scripts\check_env.py

# 8. 启动
.\.venv\Scripts\python.exe -m app.main
```

# 附录 B：命令速查卡

| 想做什么 | 命令 |
|---|---|
| 激活虚拟环境 | `.\.venv\Scripts\Activate.ps1` |
| 环境自检 | `python scripts\check_env.py` |
| 启动数据库 | `docker compose up -d` |
| 看容器状态 | `docker compose ps` |
| 停止数据库 | `docker compose stop` |
| 重新入库 | `python -m app.rag.ingest` |
| 跑检索评测 | `python eval\run_eval.py` |
| MCP + RAG 冒烟 | `python scripts\smoke_test.py` |
| 启动服务 | `python -m app.main` |
| 问一句话 | `python scripts\chat_cli.py "我还有几天年假？"` |
| 看健康状态 | 浏览器打开 `http://127.0.0.1:8000/health` |
| 看接口文档 | 浏览器打开 `http://127.0.0.1:8000/docs` |
| 聊天页 | 双击 `web\index.html` |
