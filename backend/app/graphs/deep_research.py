from __future__ import annotations

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

from app.config import get_settings
from app.models import get_chat_model

RESEARCH_PROMPT = """You are a Deep Research agent.

Workflow:
1. Clarify the question if needed.
2. Delegate gathering to the researcher subagent.
3. Delegate drafting to the writer subagent.
4. Write the final markdown report to `/workspace/report.md` via write_file.
5. Keep durable notes under `/memories/` when they should survive this thread.

Rules:
- Prefer `/workspace/` for the report and working notes.
- Call write_file for the report; a human must approve that write.
- Use MCP fetch tools when they exist; do not invent URLs or citations.
- Answer in the user's language.
"""

RESEARCHER_PROMPT = """You gather facts for the parent Deep Research agent.

- Use available fetch/search tools when present.
- Return concise notes with sources. Do not write the final report.
"""

WRITER_PROMPT = """You write the markdown research report.

- Structure: title, summary, findings, sources.
- Put the report at `/workspace/report.md` using write_file.
- Do not invent sources.
"""


def default_workspace_dir() -> Path:
    settings = get_settings()
    path = Path(settings.workspace_dir)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_research_backend(*, workspace_dir: str | Path, store) -> CompositeBackend:
    root = Path(workspace_dir)
    root.mkdir(parents=True, exist_ok=True)
    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/workspace/": FilesystemBackend(root_dir=root, virtual_mode=True),
            "/memories/": StoreBackend(
                namespace=lambda _rt: ("memories",),
                store=store,
            ),
        },
    )


def build_deep_research_agent(
    *,
    model=None,
    checkpointer=None,
    store=None,
    tools=None,
    workspace_dir: str | Path | None = None,
    **_kwargs,
):
    store = store or InMemoryStore()
    workspace = Path(workspace_dir) if workspace_dir else default_workspace_dir()
    extra_tools = list(tools or [])
    interrupt_on: dict[str, bool] = {"write_file": True}
    for tool in extra_tools:
        name = getattr(tool, "name", "") or ""
        if "fetch" in name.lower():
            interrupt_on[name] = True

    return create_deep_agent(
        model=model or get_chat_model(),
        tools=extra_tools,
        system_prompt=RESEARCH_PROMPT,
        subagents=[
            {
                "name": "researcher",
                "description": "Gather facts, citations, and source notes.",
                "system_prompt": RESEARCHER_PROMPT,
                "tools": extra_tools,
            },
            {
                "name": "writer",
                "description": "Write the markdown report into /workspace/.",
                "system_prompt": WRITER_PROMPT,
            },
        ],
        backend=build_research_backend(workspace_dir=workspace, store=store),
        interrupt_on=interrupt_on,
        checkpointer=checkpointer,
        store=store,
        name="deep_research",
    )


# Exported for langgraph.json / `langgraph dev`.
graph = build_deep_research_agent()
