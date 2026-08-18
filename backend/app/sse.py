from __future__ import annotations

import json
from typing import Any, Iterator

from langchain_core.messages import AIMessageChunk, BaseMessage


def sse_frame(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def text_from_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "".join(parts)
    return str(content)


def _interrupt_payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "value"):
        return {"type": "interrupt", "value": value.value}
    if isinstance(value, (list, tuple)) and value:
        first = value[0]
        if hasattr(first, "value"):
            return {"type": "interrupt", "value": first.value}
        return {"type": "interrupt", "value": first}
    return {"type": "interrupt", "value": value}


def encode_stream_item(item: Any) -> Iterator[dict[str, Any]]:
    """Map LangGraph astream items to a small SSE JSON schema.

    Frames:
      {"type": "token", "content": "..."}
      {"type": "message", "role": "...", "content": "..."}
      {"type": "interrupt", "value": ...}
      {"type": "tool", "name": "...", "content": "..."}
    """
    mode, data = _split_mode(item)
    if mode == "messages":
        yield from _encode_messages(data)
        return
    if mode == "updates":
        yield from _encode_updates(data)
        return


def _split_mode(item: Any) -> tuple[str, Any]:
    if isinstance(item, tuple):
        if len(item) == 3:
            _ns, mode, data = item
            return str(mode), data
        if len(item) == 2:
            mode, data = item
            if isinstance(mode, str):
                return mode, data
            return "messages", item
    return "updates", item


def _encode_messages(data: Any) -> Iterator[dict[str, Any]]:
    message = data[0] if isinstance(data, tuple) else data
    if not isinstance(message, BaseMessage):
        return
    text = text_from_content(getattr(message, "content", ""))
    if isinstance(message, AIMessageChunk):
        if text:
            yield {"type": "token", "content": text}
        return
    role = getattr(message, "type", "assistant")
    if role == "tool":
        yield {
            "type": "tool",
            "name": getattr(message, "name", ""),
            "content": text,
        }
        return
    if text:
        yield {"type": "message", "role": role, "content": text}


def _encode_updates(data: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(data, dict):
        return
    if "__interrupt__" in data:
        yield _interrupt_payload(data["__interrupt__"])
        return
    for node, update in data.items():
        if node == "__interrupt__":
            yield _interrupt_payload(update)
            continue
        if not isinstance(update, dict):
            continue
        if "__interrupt__" in update:
            yield _interrupt_payload(update["__interrupt__"])
