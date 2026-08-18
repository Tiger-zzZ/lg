from app.config import Settings
from app.mcp import load_mcp_tools, mcp_connections


def test_mcp_connections_shape(tmp_path):
    conns = mcp_connections(str(tmp_path))
    assert set(conns) == {"filesystem", "fetch"}
    assert conns["filesystem"]["transport"] == "stdio"
    assert conns["fetch"]["command"] == "uvx"


async def test_mcp_disabled_returns_empty(tmp_path):
    tools = await load_mcp_tools(
        Settings(mcp_enabled=False),
        str(tmp_path),
    )
    assert tools == []
