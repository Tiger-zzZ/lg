# A2A extra（演示互操作，不是生产依赖）

独立于主应用：不进 `backend/langgraph.json`，不改 FastAPI `/threads` `/runs/stream`。把 supervisor 的 `research_agent` worker 包成一个 A2A JSON-RPC endpoint。

依赖官方 [`a2a-sdk`](https://github.com/a2aproject/a2a-python) v1.0：`create_agent_card_routes` + `create_jsonrpc_routes`。旧的 `A2AStarletteApplication` 已删除。

## 启动

需要本机已有 `lg/backend` 的 venv（读 `.env` 里的 LLM）以及本目录的 `a2a-sdk`。

```bash
cd extras/a2a
uv sync
# 复用主后端的模型配置
cd ../../backend
# 另一个终端
cd extras/a2a
A2A_PORT=9999 uv run python server.py
```

进程会把 `lg/backend` 加进 `sys.path`，用 `build_research_agent()` 编译 worker。`cwd` 不影响 card 形状，但真 LLM 调用仍依赖 `lg/backend/.env`。更稳妥：

```bash
cd extras/a2a
uv sync
PYTHONPATH=../../backend A2A_PORT=9999 uv run python server.py
```

## 探测

```bash
curl -sS http://127.0.0.1:9999/.well-known/agent-card.json
```

JSON-RPC `message/send` 示例见 `a2a-samples` helloworld。无 SDK / 无 LLM 时，主仓库单测只断言 card 形状，不打真模型。

## 边界

- 演示 agent-to-agent 互操作，不是生产服务。
- 不注册进默认 graphs，主前端不依赖本端口。
- 取消（`cancel`）未实现。
