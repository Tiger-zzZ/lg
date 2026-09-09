# Task Plan: lg 前沿 Agent 技术重写

## Goal

把 `/Users/anno/flyfly/lg` 原地推翻重写为一个**可分阶段 commit 的前沿 Agent 学习项目**：主线是 Deep Research Agent（`deepagents`）+ Supervisor 多 Agent（`langgraph-supervisor`），基础设施只保留 Postgres checkpointer + 极简聊天前端；MCP 接入主线，A2A 作为不阻塞主线的支线。

## Next Step

计划内 Phase 1–7 已完成。后续可选：compose postgres 冒烟（本机需 docker）、前端 `LG_API_PROXY=http://127.0.0.1:8010 npm run dev`、A2A JSON-RPC `message/send` live 对打。不 push，除非再要求。

## Current Phase

complete

## Phases

### Phase 1: Requirements & Discovery

- [x] 盘点旧 lg：自研 AgentManager / workflow engine / memory / JWT / Chroma / 前端可视化编辑器
- [x] Tavily 调研 LangGraph 1.0 / deepagents / supervisor / MCP / A2A
- [x] grill-me 锁定边界（Q1–Q7）
- **Status:** complete

### Phase 2: Planning & Structure

- [x] 冻结决策：原地推翻、Deep Research + Supervisor、极简前端、Postgres checkpointer、MCP 主线、A2A 支线
- [x] 写入本计划与 findings.md
- [x] 用户确认计划（`/goal` 授权开始分阶段开发）
- **Status:** complete

### Phase 3: Skeleton（可运行 hello-agent）

- [x] 清空旧 backend/frontend 实现，保留 git 历史（未 commit）
- [x] uv 新依赖已装：langgraph 1.2.11 / deepagents 0.7.13 / langgraph-supervisor 0.0.31 / checkpoint-postgres / langchain-mcp-adapters / langgraph-cli 0.4.31
- [x] 写入 `backend/langgraph.json`（`hello` → `app/graphs/hello.py:graph`）；Studio 未实测，可随后
- [x] FastAPI：`POST /threads` + `POST /runs/stream`（SSE）；`GET /health` 经 TestClient 通过
- [x] 极简前端代码：聊天框 + token 流 + interrupt approve/reject；`node_modules` 未装，可随后
- [x] docker-compose：仅 postgres；尚未 `up`，无 DATABASE_URL 时走 InMemorySaver
- [x] 收口：`create_agent` + FakeToolChatModel；`cd lg/backend && pytest` 11 passed
- **Status:** complete

### Phase 4: Deep Research Agent（主线 A）

- [x] `create_deep_agent`：planner + researcher/writer 子 agent + FilesystemBackend
- [x] PostgresSaver checkpointer + StoreBackend 长期记忆（`/memories/`）；无 DATABASE_URL 时 InMemoryStore
- [x] `interrupt_on`：write_file；MCP fetch 工具名含 fetch 时同样 interrupt
- [x] MCP 客户端：filesystem + fetch（现成 server，`MCP_ENABLED=false` 默认关闭；server 缺失不阻塞 compile）
- [x] 产出约定：markdown 报告写 `/workspace/report.md`（FilesystemBackend virtual_mode）
- **Status:** complete

### Phase 5: Supervisor Multi-Agent（主线 C）

- [x] `create_supervisor([research_agent, writer_agent, critic_agent])`
- [x] 与 Deep Research 共用 checkpointer / store / 前端 / SSE
- [x] 前端可切换 graph：`hello` | `deep_research` | `supervisor`（下拉已有，GRAPH_BUILDERS 注册即可）
- **Status:** complete

### Phase 6: 验证与文档

- [x] 无 LLM 的图编译 / interrupt / SSE 单测（`cd lg/backend && pytest` 21 passed）
- [x] README：三条 graph、LLM / MCP / workspace 配置、`langgraph dev` 启动说明
- [x] live 冒烟：前端 `npm install` + `tsc`；`langgraph validate` 三条 graph valid；FastAPI `127.0.0.1:8010` 真 LLM hello SSE；`langgraph dev --port 2024` 加载 hello/deep_research/supervisor
- [x] Studio 修复：`deep_research` 模块级 graph 不再 bake `InMemoryStore`（否则 `GraphLoadError`）
- [x] 旧代码去向说明（git 历史即反面教材）
- **Status:** complete

### Phase 7: A2A 支线（不阻塞主线）

- [x] 独立目录 `extras/a2a/`，不进入 `langgraph.json` 默认 graphs
- [x] 最小 A2A agent card + 把 supervisor `research_agent` 暴露为 JSON-RPC endpoint（`a2a-sdk` 1.1.2：`create_agent_card_routes` + `create_jsonrpc_routes`）
- [x] README 明确：演示互操作，不是生产依赖；无 SDK 时主仓库单测 `importorskip`
- **Status:** complete

## Key Questions

1. Q1 目标？**探索前沿 Agent 技术**（不是学纯 LangGraph API，也不是做完整产品）
2. Q2 代码策略？**允许推翻重写，原地在 `lg` 仓库进行**（保留 git 历史）
3. Q3 旗舰场景？**A+C：Deep Research + Supervisor**
4. Q4 前端？**B 极简：聊天框 + 流式 + interrupt**
5. Q5 MCP/A2A？**MCP 主线（客户端接现成 server）；A2A 开独立支线，不进主流程**
6. Q6 组织形式？**当作一个项目分阶段多个 commit**，不是 `01_basics/` 教程仓库
7. Q7 数据层？**B：Postgres 只做 checkpointer；砍 JWT/Auth/Chroma/自研 memory**

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 原地推翻 `lg`，不另起仓库 | 用户明确允许推翻重写；git 历史即旧版反面教材 |
| 当项目开发，分阶段 commit | 用户不要教程目录结构，要可运行的一条主应用 |
| 旗舰 = Deep Research + Supervisor 双 graph | 覆盖 2026 两条主流形态：分层 deep agent 与 supervisor/worker |
| 前端极简（聊天+SSE+HITL） | 学习目标是 Agent 技术，不砸产品 UI |
| 砍 JWT / 自研 AgentManager / 可视化 workflow editor / Chroma | 与 LangGraph 官方 checkpointer / Studio / deepagents filesystem 重复且旧实现有结构性缺陷 |
| Postgres 只做 `PostgresSaver` + 可选 `PostgresStore` | LangGraph 1.0 生产标准；满足「保留数据库但只服务 Agent 状态」 |
| MCP 只做客户端 | deepagents 原生支持 `tools=` 接 MCP；自写 MCP server 偏离主线 |
| A2A 独立 `extras/a2a/` | 2026 已有 v1.0（Linux Foundation），值得体验，但不能拖主线 |
| 参考而不 fork | 复用 deepagents / langgraph-supervisor / agent-service-toolkit 的模式，不拷贝其业务代码 |
| 按阶段 git commit，不 push | 用户 `/goal` 授权每个阶段 commit；push 仍未要求 |
| MCP 默认关闭，失败不阻塞 compile | 图必须无 MCP server / 无真 LLM 也能编译；`MCP_ENABLED=true` 才 spawn 官方 filesystem + fetch |
| HITL resume 按 graph 适配 | 前端继续发 `approve`/`reject`；`deep_research` 转成 `{decisions:[{type}]}` |
| StoreBackend `/memories/` + FilesystemBackend `/workspace/` | 官方 CompositeBackend 路由；无 DATABASE_URL 用 InMemoryStore |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| 审查后端的 Explore agent 两次被中断 | 2 | 改为抽样阅读 base.py / main.py / pyproject.toml + VALIDATION_REPORT，足够支撑「推翻」决策 |
| planning-with-files:plan-zh skill 名无效 | 1 | 直接跑 `init-session.sh` 并手写中文计划 |
| 旧 DSH eval 计划曾被 hook 注入 | 1 | 本 PLAN_ID=`2026-09-08-lg-agent-rewrite` 覆盖，忽略他仓计划 |
| `uv sync` 在 flyfly 根目录失败 | 1 | 必须在 `lg/backend` 执行；venv/lock 后来已生成 |
| `GenericFakeChatModel` 无 `bind_tools` | 1 | hello 图编译测试失败；收口时换支持 tool calling 的假模型 |
| `create_react_agent` LangGraph 1.0 弃用警告 | 1 | 改为 `from langchain.agents import create_agent` |
| 从 flyfly 根跑 pytest 扫到 pubmed_mcp | 1 | 必须 `cd lg/backend && pytest`；README 已注明 |
| `GenericFakeChatModel.bind_tools` NotImplemented | 1 | 测试用 `FakeToolChatModel`（FakeMessagesListChatModel + bind_tools 返回 self） |
| `langgraph-supervisor` 内部仍调 `create_react_agent` | 1 | 我们的 worker 用 `create_agent`；supervisor 包警告可忽略，不自研调度器 |
| 官方 `@modelcontextprotocol/server-fetch` npm 包已不作为主路径 | 1 | fetch 用官方 Python `uvx mcp-server-fetch`；filesystem 仍用 `npx @modelcontextprotocol/server-filesystem` |
| `langgraph dev` GraphLoadError：deep_research 模块级 graph 含自定义 InMemoryStore | 1 | 去掉 `store = store or InMemoryStore()`；Studio 路径 store=None，StoreBackend 运行时 `get_store()` |
| 本机 8000 被 Code Helper 占用 | 1 | 后端改 8010；前端 `LG_API_PROXY`；不杀 8000 |
| `uv run uvicorn` / `uv run python -m uvicorn` 找不到模块 | 1 | 用 `backend/.venv/bin/uvicorn`，且 cwd=`lg/backend` 才能读 `.env` |
| 本机无 docker | 1 | compose postgres 冒烟跳过，走 InMemorySaver/Store |

## Notes

- 实施前必须再读本文件 Goal / Decisions。
- 外部网页内容只进 `findings.md`。
- Phase 7 可在 Phase 6 之后单独开，也可与 Phase 5 并行，但不得改主 graph 的 API 形状。
- 计划结构（A+C / MCP 主线 / A2A 支线 / Postgres checkpointer）不改。Phase 1–7 代码已落地。
