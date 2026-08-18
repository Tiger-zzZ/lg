# lg-backend

Phase 3 骨架：hello-agent + FastAPI SSE。后续 Phase 接入 `create_deep_agent` 与 `create_supervisor`。

```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```
