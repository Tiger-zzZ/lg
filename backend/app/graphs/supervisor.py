from langchain.agents import create_agent
from langgraph_supervisor import create_supervisor

from app.models import get_chat_model

SUPERVISOR_PROMPT = """You coordinate three workers: research_agent, writer_agent, critic_agent.

Flow:
1. Send the question to research_agent.
2. Send the research notes to writer_agent for a markdown draft.
3. Send the draft to critic_agent.
4. If the critic requests changes, loop writer_agent then critic_agent once more.
5. When the critic accepts, reply to the user with the final markdown.

Do the work through workers. Do not invent sources.
Answer in the user's language.
"""

RESEARCH_AGENT_PROMPT = """You are research_agent. Collect facts and sources for the supervisor.

Use fetch/search tools when they exist. Return concise notes with sources.
Do not write the full report.
"""

WRITER_AGENT_PROMPT = """You are writer_agent. Turn research notes into a markdown report.

Structure: title, summary, findings, sources. Do not invent sources.
"""

CRITIC_AGENT_PROMPT = """You are critic_agent. Review the draft for gaps, unsupported claims, and missing sources.

If it is good enough, reply with ACCEPT and a one-line reason.
If not, reply with REVISE and a short bullet list of required changes.
"""


def build_supervisor_graph(
    *,
    model=None,
    checkpointer=None,
    store=None,
    tools=None,
    **_kwargs,
):
    chat = model or get_chat_model()
    extra_tools = list(tools or [])
    research_agent = create_agent(
        model=chat,
        tools=extra_tools,
        system_prompt=RESEARCH_AGENT_PROMPT,
        name="research_agent",
    )
    writer_agent = create_agent(
        model=chat,
        tools=[],
        system_prompt=WRITER_AGENT_PROMPT,
        name="writer_agent",
    )
    critic_agent = create_agent(
        model=chat,
        tools=[],
        system_prompt=CRITIC_AGENT_PROMPT,
        name="critic_agent",
    )
    return create_supervisor(
        [research_agent, writer_agent, critic_agent],
        model=chat,
        prompt=SUPERVISOR_PROMPT,
        supervisor_name="supervisor",
    ).compile(checkpointer=checkpointer, store=store, name="supervisor")


# Exported for langgraph.json / `langgraph dev`.
graph = build_supervisor_graph()
