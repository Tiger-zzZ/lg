"""LangGraph store: Postgres when DATABASE_URL is set, otherwise in-memory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.store.memory import InMemoryStore

from app.config import Settings


@asynccontextmanager
async def open_store(settings: Settings) -> AsyncIterator:
    """Long-term store for StoreBackend `/memories/`.

    `langgraph dev` injects its own store and ignores this.
    """
    if not settings.database_url:
        yield InMemoryStore()
        return

    from langgraph.store.postgres import PostgresStore

    cm = PostgresStore.from_conn_string(
        settings.database_url,
        pool_config={"min_size": 1, "max_size": 5},
    )
    store = cm.__enter__()
    try:
        store.setup()
        yield store
    finally:
        cm.__exit__(None, None, None)
