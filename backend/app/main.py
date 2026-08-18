from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.checkpointer import open_checkpointer
from app.config import get_settings
from app.graphs import GRAPH_BUILDERS, compile_graph
from app.graphs.deep_research import default_workspace_dir
from app.hitl import wrap_resume
from app.mcp import load_mcp_tools
from app.models import get_chat_model
from app.sse import encode_stream_item, sse_frame
from app.store import open_store

graphs: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    workspace_dir = default_workspace_dir()
    async with (
        open_checkpointer(settings) as checkpointer,
        open_store(settings) as store,
    ):
        model = get_chat_model(settings)
        tools = await load_mcp_tools(settings, str(workspace_dir))
        for graph_id in GRAPH_BUILDERS:
            graphs[graph_id] = compile_graph(
                graph_id,
                checkpointer=checkpointer,
                model=model,
                store=store,
                tools=tools,
                workspace_dir=workspace_dir,
            )
        yield
        graphs.clear()


app = FastAPI(title="lg agent runtime", version="0.2.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ThreadCreate(BaseModel):
    graph_id: str = "hello"


class ThreadOut(BaseModel):
    thread_id: str
    graph_id: str


class StreamRequest(BaseModel):
    graph_id: str = "hello"
    thread_id: str
    message: str | None = None
    resume: Any | None = Field(
        default=None,
        description="HITL resume value; when set, message is ignored",
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    current = get_settings()
    return {
        "status": "ok",
        "graphs": list(graphs),
        "llm_configured": bool(current.openai_api_key),
        "model": current.openai_model,
        "checkpointer": "postgres" if current.database_url else "memory",
    }


@app.get("/graphs")
async def list_graphs() -> dict[str, list[str]]:
    return {"graphs": list(graphs)}


@app.post("/threads", response_model=ThreadOut)
async def create_thread(body: ThreadCreate) -> ThreadOut:
    if body.graph_id not in graphs:
        raise HTTPException(status_code=404, detail=f"unknown graph: {body.graph_id}")
    return ThreadOut(thread_id=str(uuid4()), graph_id=body.graph_id)


@app.post("/runs/stream")
async def stream_run(body: StreamRequest) -> StreamingResponse:
    graph = graphs.get(body.graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail=f"unknown graph: {body.graph_id}")
    if body.resume is None and not (body.message or "").strip():
        raise HTTPException(status_code=400, detail="message or resume is required")

    payload: Any
    if body.resume is not None:
        payload = Command(resume=wrap_resume(body.graph_id, body.resume))
    else:
        payload = {"messages": [HumanMessage(content=body.message or "")]}

    config = {"configurable": {"thread_id": body.thread_id}}

    async def event_source():
        try:
            async for item in graph.astream(
                payload,
                config=config,
                stream_mode=["messages", "updates"],
                subgraphs=True,
            ):
                for frame in encode_stream_item(item):
                    yield sse_frame(frame)
            yield sse_frame({"type": "done"})
        except Exception as exc:
            yield sse_frame({"type": "error", "content": str(exc)})

    return StreamingResponse(event_source(), media_type="text/event-stream")
