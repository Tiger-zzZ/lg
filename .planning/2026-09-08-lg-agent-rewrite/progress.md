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

- **Status:** in-progress
- 已完成：无 LLM 编译 / interrupt / SSE 单测；README 三条 graph
- 未完成：前端 `npm install`、`langgraph dev`、真 LLM 对话

### Phase 7: A2A

- **Status:** pending（不阻塞主线）

## Test Results

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| `cd lg/backend && pytest` | 无 LLM | 全绿 | 20 passed | pass |
| `test_hello_graph_compiles` | FakeToolChatModel | 可 compile + invoke | hi | pass |
| `test_interrupt_and_resume` | confirm_action → Command(resume) | HITL 再恢复 | 已按人类决定处理 | pass |
| `test_deep_research_compiles` | FakeToolChatModel | 含 HITL 节点 | pass | pass |
| `test_deep_research_write_file_interrupt` | write_file → wrap_resume(approve) | HITL 再恢复 | pass | pass |
| `test_supervisor_compiles` | FakeToolChatModel | 含四个节点 | pass | pass |
| `test_health_and_threads` | TestClient | graphs 含三条 | pass | pass |
| 从 flyfly 根 `pytest` | 默认收集 | 只跑 lg | 扫到 pubmed_mcp | invalid / 不要这样跑 |
| `langgraph dev` / 前端 | — | 可启动 | 未跑 | skipped |

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

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | Phase 4/5 complete；Phase 6 live 冒烟未做 |
| Where am I going? | Phase 6：`langgraph dev` / 前端 / 真 LLM；然后可选 Phase 7 A2A |
| What's the goal? | Deep Research + Supervisor 前沿 Agent 学习项目 |
| What have I learned? | deepagents HITL resume 是 `{decisions:[{type}]}`；MCP 必须可选；pytest / uv 必须在 `lg/backend` |
| What have I done? | 三条 graph + SSE/HITL + 可选 MCP + StoreBackend；20 tests pass |
