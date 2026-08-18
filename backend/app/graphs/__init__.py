from collections.abc import Callable

from langgraph.graph.state import CompiledStateGraph

from app.graphs.deep_research import build_deep_research_agent
from app.graphs.hello import build_hello_agent
from app.graphs.supervisor import build_supervisor_graph

GraphBuilder = Callable[..., CompiledStateGraph]

GRAPH_BUILDERS: dict[str, GraphBuilder] = {
    "hello": build_hello_agent,
    "deep_research": build_deep_research_agent,
    "supervisor": build_supervisor_graph,
}


def compile_graph(
    graph_id: str,
    *,
    checkpointer=None,
    model=None,
    store=None,
    tools=None,
    workspace_dir=None,
) -> CompiledStateGraph:
    try:
        builder = GRAPH_BUILDERS[graph_id]
    except KeyError as exc:
        raise KeyError(f"unknown graph: {graph_id}") from exc
    return builder(
        model=model,
        checkpointer=checkpointer,
        store=store,
        tools=tools,
        workspace_dir=workspace_dir,
    )
