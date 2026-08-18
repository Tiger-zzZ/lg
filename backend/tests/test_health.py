from fastapi.testclient import TestClient

from app.main import app


def test_health_and_threads():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        body = health.json()
        assert body["status"] == "ok"
        assert "hello" in body["graphs"]
        assert "deep_research" in body["graphs"]
        assert "supervisor" in body["graphs"]
        assert "llm_configured" in body
        assert "model" in body
        assert body["checkpointer"] in {"memory", "postgres"}
        created = client.post("/threads", json={"graph_id": "hello"})
        assert created.status_code == 200
        assert created.json()["thread_id"]
