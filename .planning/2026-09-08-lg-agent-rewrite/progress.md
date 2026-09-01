# Progress Log

## Session: 2026-09-08 / 2026-09-09

### Phase 1: Requirements & Discovery

- **Status:** complete
- **Started:** 2026-09-08

### Phase 2: Planning & Structure

- **Status:** complete

### Phase 3: Skeleton

- **Status:** complete
- Started: 2026-09-08
- Closed: 2026-09-09
- Actions taken:
  - `git rm` 清空旧实现，未 commit
  - hello-agent 改为 `langchain.agents.create_agent`
  - 测试假模型 `FakeToolChatModel`（`bind_tools` 返回 self）
  - LLM 配置路径落到 `lg/backend/.env`（`OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`）
  - `GET /health` 增加 `llm_configured` / `model` / `checkpointer`
  - `cd lg/backend && pytest` → 11 passed（当时）
- Residual (non-blocking):
  - 前端未 `npm install`
  - `langgraph dev` 未冒烟
  - compose postgres 未 `up`（无 DATABASE_URL 走内存）

### Phase 4: Deep Research Agent

- **Status:** complete
- Closed: 2026-09-09
- Actions taken:
  - `app/graphs/deep_research.py`：`create_deep_agent` + researcher/writer
  - `CompositeBackend`：`/workspace/` → FilesystemBackend(virtual_mode)；`/memories/` → StoreBackend
  - `interrupt_on={"write_file": True}`；MCP fetch 工具名含 fetch 时同样 interrupt
  - MCP 客户端：`MCP_ENABLED` 默认 false；server 缺失返回 `[]`
  - HITL：`wrap_resume` 把前端 `approve`/`reject` 转成 deepagents `{decisions:[{type}]}`

### Phase 5: Supervisor Multi-Agent

- **Status:** complete
- Closed: 2026-09-09
- Actions taken:
  - `app/graphs/supervisor.py`：`create_supervisor([research_agent, writer_agent, critic_agent])`
  - 共用 checkpointer / store / SSE / 前端 graph 下拉
  - `langgraph.json` 注册 `hello` / `deep_research` / `supervisor`
  - `cd lg/backend && pytest` → 20 passed

### Phase 6: 验证与文档

- **Status:** complete
- Closed: 2026-09-09
- Actions taken:
  - `cd lg/backend && pytest` → 21 passed（含 `test_deep_research_studio_export_has_no_custom_store`）
  - 前端 `npm install` + `tsc` 绿；提交 `frontend/package-lock.json`
  - `langgraph validate`：hello / deep_research / supervisor valid
  - FastAPI `127.0.0.1:8010`（cwd=`lg/backend`）`/health` `llm_configured:true`；hello 真 LLM SSE 成功
  - `langgraph dev --no-browser --port 2024` 加载三条 graph；`GET /ok` → `{"ok":true}`
  - 去掉 deep_research 模块级 baked `InMemoryStore`，Studio 不再 `GraphLoadError`
  - README / backend README：必须在 `lg/backend` 启动；8000 占用时 8010 + `LG_API_PROXY`
- Residual (non-blocking):
  - 本机无 docker，compose postgres 跳过
  - 8000 仍被 Code Helper 占用，不要杀
  - 前端 `npm run dev` 需 `LG_API_PROXY=http://127.0.0.1:8010`

### Phase 7: A2A

- **Status:** pending（不阻塞主线）

## Test Results

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| `cd lg/backend && pytest` | 无 LLM | 全绿 | 21 passed | pass |
| `test_hello_graph_compiles` | FakeToolChatModel | 可 compile + invoke | hi | pass |
| `test_interrupt_and_resume` | confirm_action → Command(resume) | HITL 再恢复 | 已按人类决定处理 | pass |
| `test_deep_research_compiles` | FakeToolChatModel | 含 HITL 节点 | pass | pass |
| `test_deep_research_write_file_interrupt` | write_file → wrap_resume(approve) | HITL 再恢复 | pass | pass |
| `test_supervisor_compiles` | FakeToolChatModel | 含四个节点 | pass | pass |
| `test_health_and_threads` | TestClient | graphs 含三条 | pass | pass |
| 从 flyfly 根 `pytest` | 默认收集 | 只跑 lg | 扫到 pubmed_mcp | invalid / 不要这样跑 |
| `langgraph validate` | 三条 graph | valid | valid | pass |
| `langgraph dev --port 2024` | Studio 加载 | `/ok` true | `{"ok":true}` | pass |
| 真 LLM hello SSE | FastAPI 8010 | 有回复 | thread `5f315f45-...` 回复自我介绍 | pass |
| frontend `tsc` | npm install 后 | 通过 | 通过 | pass |
| compose postgres | docker | 可 up | 本机无 docker | skipped |

## Error Log

| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-09-08 | Explore 审查 agent 被中断 | 2 | 抽样阅读关键文件 |
| 2026-09-08 | Skill 名 `planning-with-files:plan-zh` 无效 | 1 | 直接 `init-session.sh` |
| 2026-09-08 | Tavily 429 | 1 | 用已缓存官方文档继续 |
| 2026-09-08 | `uv sync` 在 flyfly 根失败 | 2 | 在 `lg/backend` 执行 |
| 2026-09-09 | FakeChatModel 无 `bind_tools` | 1 | `FakeToolChatModel` |
| 2026-09-09 | `create_react_agent` V1 弃用 | 1 | `langchain.agents.create_agent` |
| 2026-09-09 | supervisor 包内部仍 `create_react_agent` | 1 | worker 用 `create_agent`；包警告可忽略 |
| 2026-09-09 | `langgraph dev` GraphLoadError（自定义 InMemoryStore） | 1 | 模块级 graph 不再 bake store |
| 2026-09-09 | cwd≠backend → `llm_configured:false` | 1 | 必须从 `lg/backend` 启动 uvicorn |
| 2026-09-09 | 端口 8000 被占用 | 1 | 改 8010 + `LG_API_PROXY` |

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | Phase 6 complete；准备 Phase 7 A2A extras |
| Where am I going? | `extras/a2a/` 暴露 supervisor `research_agent`；不进默认 graphs |
| What's the goal? | Deep Research + Supervisor 前沿 Agent 学习项目 |
| What have I learned? | Studio 不能 bake 自定义 store；uvicorn 必须在 `lg/backend` 才能读 `.env`；deepagents HITL resume 是 `{decisions:[{type}]}` |
| What have I done? | 三条 graph + SSE/HITL + 可选 MCP + StoreBackend；live 冒烟；21 tests pass |
