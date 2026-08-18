from datetime import datetime

from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.types import interrupt

from app.models import get_chat_model

HELLO_PROMPT = """You are a hello-agent used to verify the LangGraph runtime.

Rules:
- Answer briefly in the user's language.
- Use get_time when asked about the current time.
- If the user asks to perform a sensitive action (delete, send, pay, deploy),
  call confirm_action first and wait for the human decision.
- Do not invent tools.
"""


@tool
def get_time() -> str:
    """Return the current local time in ISO format."""
    return datetime.now().isoformat(timespec="seconds")


@tool
def confirm_action(action: str) -> str:
    """Ask a human to approve a sensitive action before continuing."""
    decision = interrupt(
        {
            "type": "approval",
            "action": action,
            "prompt": f"是否允许执行：{action}？",
        }
    )
    return f"human_decision={decision}"


def build_hello_agent(*, model=None, checkpointer=None, **_kwargs):
    return create_agent(
        model=model or get_chat_model(),
        tools=[get_time, confirm_action],
        system_prompt=HELLO_PROMPT,
        checkpointer=checkpointer,
        name="hello",
    )


# Exported for langgraph.json / `langgraph dev`.
graph = build_hello_agent()
