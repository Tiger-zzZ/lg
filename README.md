# lg — Deep Research + Supervisor 学习项目

旧实现（自研 AgentManager / JWT / Chroma / 可视化编辑器）已清空，git 历史保留作反面教材。

当前阶段是 **Phase 4/5**：同一套 SSE / checkpointer / 极简前端上挂三条 graph：

| graph | 形态 |
|-------|------|
| `hello` | `create_agent` + HITL（骨架） |
| `deep_research` | `create_deep_agent` + researcher/writer + FilesystemBackend `/workspace/` + StoreBackend `/memories/` + `interrupt_on write_file` + 可选 MCP |
| `supervisor` | `create_supervisor([research_agent, writer_agent, critic_agent])` |

Phase 6 补文档与更多验证。Phase 7（A2A）不进默认 `langgraph.json`。

## LLM 配置（开发阶段必填才能对话）

单测不打真模型。要在 UI / Studio 里跑，把 key 写进 **`lg/backend/.env`**（已 gitignore）。`langgraph.json` 的 `"env": ".env"` 和 FastAPI 都读这个文件。

```bash
cd backend
cp .env.example .env
```

| 变量 | 作用 |
|------|------|
| `OPENAI_API_KEY` | 必填。任意 OpenAI Chat Completions 兼容网关的 key |
| `OPENAI_BASE_URL` | 可选。留空走官方 OpenAI；SiliconFlow / DeepSeek / ModelScope 填其 `/v1` |
| `OPENAI_MODEL` | 模型 id。可写 `gpt-4o-mini` 或带 provider 前缀 `openai:gpt-4o-mini` |
| `DATABASE_URL` | 可选。空则 InMemorySaver + InMemoryStore；compose postgres 示例见 `.env.example` |
| `WORKSPACE_DIR` | Deep Research 报告目录，默认 `backend/.workspace`，映射 `/workspace/` |
| `MCP_ENABLED` | 默认 `false`。`true` 时启动官方 filesystem + fetch MCP；server 不在也不阻塞编译 |

示例：

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# SiliconFlow
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_MODEL=deepseek-ai/DeepSeek-V3.1
```

`GET /health` 会返回 `llm_configured` / `model` / `checkpointer`，不回 key。

## 跑起来

```bash
# 1. Postgres（checkpointer + store，可先不启，后端会回落到内存）
docker compose up -d postgres

# 2. 后端（必须在 lg/backend）
cd backend
cp .env.example .env   # 填 OPENAI_API_KEY；兼容网关可填 OPENAI_BASE_URL
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000

# 3. 前端
cd ../frontend
npm install
npm run dev            # http://localhost:3000

# 4. 可选：LangGraph Studio
cd backend
uv run langgraph dev
```

前端下拉框切换 `hello` / `deep_research` / `supervisor`。Deep Research 写 `/workspace/report.md` 时会 interrupt，点 approve / reject。

可选 MCP（不自写 server）：

```bash
# 需要本机有 npx 和 uvx
MCP_ENABLED=true
```

- filesystem: `npx -y @modelcontextprotocol/server-filesystem <workspace>`
- fetch: `uvx mcp-server-fetch`

## 接口

| 方法 | 路径 | 作用 |
|------|------|------|
| GET | `/health` | 存活 + 已加载 graph |
| GET | `/graphs` | graph 列表 |
| POST | `/threads` | `{graph_id}` → `{thread_id}` |
| POST | `/runs/stream` | SSE：`message` 开跑，`resume` 恢复 interrupt |

SSE 帧：`token` / `message` / `tool` / `interrupt` / `done` / `error`。

`resume` 对 `hello` 是原始字符串；对 `deep_research` 后端会把 `approve`/`reject` 转成 deepagents HITL 的 `{decisions:[{type}]}`。

## 测试（不打真 LLM）

```bash
cd backend
uv run pytest          # 必须在 lg/backend，不要从 flyfly 根跑
```
