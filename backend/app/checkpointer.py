from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.memory import InMemorySaver

from app.config import Settings


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncIterator:
    """Postgres when DATABASE_URL is set, otherwise in-memory.

    `langgraph dev` injects its own checkpointer and ignores this.
    """
    if not settings.database_url:
        yield InMemorySaver()
        return

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as saver:
        await saver.setup()
        yield saver
