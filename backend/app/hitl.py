"""Normalize HITL resume payloads so the frontend can keep sending approve/reject."""

from __future__ import annotations

from typing import Any

_APPROVE = {"approve", "approved", "yes", "y"}


def wrap_resume(graph_id: str, resume: Any) -> Any:
    """hello uses a raw interrupt value; deepagents HITL expects `{decisions: [...]}`."""
    if resume is None or not isinstance(resume, str):
        return resume
    if graph_id != "deep_research":
        return resume
    kind = "approve" if resume.strip().lower() in _APPROVE else "reject"
    decision: dict[str, Any] = {"type": kind}
    if kind == "reject":
        decision["message"] = "rejected by human"
    return {"decisions": [decision]}
