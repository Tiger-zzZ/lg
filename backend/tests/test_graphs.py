from pathlib import Path

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from app.graphs import GRAPH_BUILDERS, compile_graph
from app.graphs.deep_research import build_deep_research_agent
from app.graphs.supervisor import build_supervisor_graph
from app.hitl import wrap_resume
from tests.fakes import FakeToolChatModel


def test_all_graphs_registered():
    assert set(GRAPH_BUILDERS) == {"hello", "deep_research", "supervisor"}


def test_deep_research_compiles(tmp_path: Path):
    graph = build_deep_research_agent(
        model=FakeToolChatModel(responses=[AIMessage(content="ok")]),
        checkpointer=InMemorySaver(),
        store=InMemoryStore(),
        workspace_dir=tmp_path,
    )
    assert graph is not None
    assert "model" in graph.nodes
    assert "tools" in graph.nodes
    assert "HumanInTheLoopMiddleware.after_model" in graph.nodes


def test_deep_research_write_file_interrupt(tmp_path: Path):
    graph = build_deep_research_agent(
        model=FakeToolChatModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "write_file",
                            "args": {
                                "file_path": "/workspace/report.md",
                                "content": "# Report\n",
                            },
                            "id": "call-write",
                        }
                    ],
                ),
                AIMessage(content="报告已写入 /workspace/report.md"),
            ]
        ),
        checkpointer=InMemorySaver(),
        store=InMemoryStore(),
        workspace_dir=tmp_path,
    )
    config = {"configurable": {"thread_id": "t-write"}}
    result = graph.invoke(
        {"messages": [{"role": "user", "content": "写一份报告"}]},
        config=config,
    )
    interrupts = result.get("__interrupt__") or []
    assert interrupts, "expected HITL interrupt from write_file"

    resumed = graph.invoke(
        Command(resume=wrap_resume("deep_research", "approve")),
        config=config,
    )
    assert resumed["messages"][-1].content


def test_research_agent_builder_compiles():
    from app.graphs.supervisor import build_research_agent

    graph = build_research_agent(
        model=FakeToolChatModel(responses=[AIMessage(content="notes")])
    )
    assert graph is not None


def test_supervisor_compiles():
    graph = build_supervisor_graph(
        model=FakeToolChatModel(responses=[AIMessage(content="done")]),
        checkpointer=InMemorySaver(),
        store=InMemoryStore(),
    )
    assert graph is not None
    for name in ("supervisor", "research_agent", "writer_agent", "critic_agent"):
        assert name in graph.nodes


def test_deep_research_studio_export_has_no_custom_store(tmp_path: Path):
    graph = build_deep_research_agent(
        model=FakeToolChatModel(responses=[AIMessage(content="ok")]),
        workspace_dir=tmp_path,
    )
    assert getattr(graph, "store", None) is None


def test_compile_graph_unknown():
    try:
        compile_graph("nope")
    except KeyError as exc:
        assert "unknown graph" in str(exc)
    else:
        raise AssertionError("expected KeyError")


def test_wrap_resume_hello_passthrough():
    assert wrap_resume("hello", "approve") == "approve"


def test_wrap_resume_deep_research():
    assert wrap_resume("deep_research", "approve") == {
        "decisions": [{"type": "approve"}]
    }
    assert wrap_resume("deep_research", "reject") == {
        "decisions": [{"type": "reject", "message": "rejected by human"}]
    }
