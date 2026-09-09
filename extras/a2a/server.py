"""Minimal A2A endpoint wrapping supervisor research_agent.

Demo interop only. Not a production dependency. Does not change the main
graph API and is not registered in langgraph.json.

Run from extras/a2a after `uv sync`:

    uv run python server.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Role,
    TaskState,
)
from starlette.applications import Starlette

HOST = os.environ.get("A2A_HOST", "127.0.0.1")
PORT = int(os.environ.get("A2A_PORT", "9999"))
BASE_URL = os.environ.get("A2A_URL", f"http://{HOST}:{PORT}/")

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def build_agent_card(*, url: str = BASE_URL) -> AgentCard:
    skill = AgentSkill(
        id="research_notes",
        name="Research notes",
        description="Collect concise notes and sources for a research question.",
        tags=["research", "notes"],
        input_modes=["text/plain"],
        output_modes=["text/plain"],
    )
    return AgentCard(
        name="lg-research-agent",
        description=(
            "A2A demo wrapping the supervisor research_agent worker. "
            "Interop sample, not a production service."
        ),
        version="0.0.1",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                url=url,
                protocol_version="1.0",
            )
        ],
        skills=[skill],
    )


def last_ai_text(result: dict) -> str:
    messages = result.get("messages") or []
    for message in reversed(messages):
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            text = "".join(parts).strip()
            if text:
                return text
    return ""


class ResearchAgentExecutor(AgentExecutor):
    """Run supervisor research_agent once per A2A message."""

    def __init__(self, graph=None):
        self._graph = graph

    def _graph_or_build(self):
        if self._graph is not None:
            return self._graph
        from app.graphs.supervisor import build_research_agent

        self._graph = build_research_agent()
        return self._graph

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)
        if context.current_task is None:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(
            event_queue=event_queue, task_id=task.id, context_id=task.context_id
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message(
                "research_agent is collecting notes...",
                role=Role.ROLE_AGENT,
            ),
        )
        query = get_message_text(context.message) if context.message else ""
        if not query:
            result_text = "No text input is provided."
        else:
            graph = self._graph_or_build()
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": query}]}
            )
            result_text = last_ai_text(result) or "research_agent returned no text."
        await updater.add_artifact(
            parts=[new_text_part(text=result_text, media_type="text/plain")]
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message(result_text, role=Role.ROLE_AGENT),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel is not supported.")


def build_app(*, executor: AgentExecutor | None = None, url: str = BASE_URL) -> Starlette:
    agent_card = build_agent_card(url=url)
    request_handler = DefaultRequestHandler(
        agent_executor=executor or ResearchAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, "/"))
    return Starlette(routes=routes)


app = build_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
