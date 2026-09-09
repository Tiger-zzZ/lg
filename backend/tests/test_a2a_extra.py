from __future__ import annotations

import sys
from pathlib import Path

import pytest

EXTRAS = Path(__file__).resolve().parents[2] / "extras" / "a2a"
if str(EXTRAS) not in sys.path:
    sys.path.insert(0, str(EXTRAS))


a2a = pytest.importorskip("a2a")


def test_research_agent_card_shape():
    from google.protobuf.json_format import MessageToDict

    from server import build_agent_card

    card = build_agent_card(url="http://127.0.0.1:9999/")
    payload = MessageToDict(card, preserving_proto_field_name=True)
    assert payload["name"] == "lg-research-agent"
    assert payload["skills"][0]["id"] == "research_notes"
    assert payload["supported_interfaces"][0]["protocol_binding"] == "JSONRPC"
    assert payload["supported_interfaces"][0]["url"] == "http://127.0.0.1:9999/"


def test_a2a_app_exposes_agent_card():
    from starlette.testclient import TestClient

    from server import ResearchAgentExecutor, build_app

    class DummyGraph:
        async def ainvoke(self, payload):
            from langchain_core.messages import AIMessage

            return {"messages": [AIMessage(content="notes: demo")]}

    app = build_app(
        executor=ResearchAgentExecutor(graph=DummyGraph()),
        url="http://127.0.0.1:9999/",
    )
    with TestClient(app) as client:
        card = client.get("/.well-known/agent-card.json")
        assert card.status_code == 200
        body = card.json()
        assert body["name"] == "lg-research-agent"
        interfaces = body.get("supportedInterfaces") or body.get("supported_interfaces") or []
        assert any(
            (iface.get("protocolBinding") or iface.get("protocol_binding")) == "JSONRPC"
            for iface in interfaces
        )
