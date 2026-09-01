# lg-backend

三条 graph 共用 FastAPI SSE / checkpointer / store：

| graph | 入口 |
|-------|------|
| `hello` | `app/graphs/hello.py` |
| `deep_research` | `app/graphs/deep_research.py` |
| `supervisor` | `app/graphs/supervisor.py` |

必须在本目录启动，才会读到 `.env`：

```bash
cd backend
cp .env.example .env   # 填 OPENAI_API_KEY；兼容网关再填 OPENAI_BASE_URL
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

`8000` 被占用时换端口，前端用 `LG_API_PROXY` 对齐：

```bash
uv run uvicorn app.main:app --reload --port 8010
# 另一个终端
cd ../frontend
LG_API_PROXY=http://127.0.0.1:8010 npm run dev
```

可选 Studio：`uv run langgraph dev --no-browser`。模块级 graph 不要自带 store/checkpointer，Studio 会注入。

测试：`uv run pytest`（不要从 flyfly 根跑）。
