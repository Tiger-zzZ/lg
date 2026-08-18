from app.sse import encode_stream_item, sse_frame, text_from_content
from app.graphs import GRAPH_BUILDERS


def test_sse_frame_shape():
    frame = sse_frame({"type": "token", "content": "你好"})
    assert frame.startswith("data: {")
    assert '"type": "token"' in frame
    assert frame.endswith("\n\n")


def test_encode_interrupt_update():
    frames = list(encode_stream_item(("updates", {"__interrupt__": [{"value": "x"}]})))
    assert frames
    assert frames[0]["type"] == "interrupt"


def test_text_from_content_blocks():
    assert text_from_content([{"type": "text", "text": "ab"}, {"type": "text", "text": "c"}]) == "abc"


def test_graphs_registered():
    assert set(GRAPH_BUILDERS) >= {"hello", "deep_research", "supervisor"}
