from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graphs.hello import build_hello_agent
from app.sse import encode_stream_item, sse_frame
from tests.fakes import FakeToolChatModel


def test_hello_graph_compiles():
    graph = build_hello_agent(
        model=FakeToolChatModel(responses=[AIMessage(content="hi")]),
        checkpointer=InMemorySaver(),
    )
    assert graph is not None
    result = graph.invoke(
        {"messages": [{"role": "user", "content": "hi"}]},
        {"configurable": {"thread_id": "t-compile"}},
    )
    assert result["messages"][-1].content == "hi"


def test_interrupt_and_resume():
    graph = build_hello_agent(
        model=FakeToolChatModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "confirm_action",
                            "args": {"action": "delete files"},
                            "id": "call-1",
                        }
                    ],
                ),
                AIMessage(content="已按人类决定处理。"),
            ]
        ),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "t-interrupt"}}
    result = graph.invoke(
        {"messages": [{"role": "user", "content": "请删除文件"}]},
        config=config,
    )
    interrupts = result.get("__interrupt__") or []
    assert interrupts, "expected HITL interrupt from confirm_action"

    resumed = graph.invoke(Command(resume="approve"), config=config)
    text = resumed["messages"][-1].content
    assert "人类" in text or "决定" in text or text


def test_sse_frame_shape():
    frame = sse_frame({"type": "token", "content": "你好"})
    assert frame.startswith("data: {")
    assert '"type": "token"' in frame
    assert frame.endswith("\n\n")


def test_encode_interrupt_update():
    frames = list(encode_stream_item(("updates", {"__interrupt__": [{"value": "x"}]})))
    assert frames
    assert frames[0]["type"] == "interrupt"
