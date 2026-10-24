# -*- coding: utf-8 -*-
"""
Shared resources: database operations, the process-wide PyPI client, and the
startup/shutdown hooks that manage them.

Author:
    Mike Ryan

License:
    MIT License
"""

from datetime import timedelta
from typing import Any

import httpx
from dsg_lib.async_database_functions import database_operations
from dsg_lib.async_database_functions.database_operations import DatabaseErrorResult
from loguru import logger
from sqlalchemy import text

from . import __version__
from .db_init import async_db
from .resolver.index import PyPIIndex
from .settings import settings

db_ops = database_operations.DatabaseOperations(async_db)

# Created in startup(): an httpx client binds to the running event loop.
pypi_client: httpx.AsyncClient | None = None
pypi_index: PyPIIndex | None = None


def ensure_ok(result: Any) -> Any:
    """dsg_lib returns a DatabaseErrorResult instead of raising; turn it into an exception."""
    if isinstance(result, DatabaseErrorResult):
        raise RuntimeError(
            f"database error: {result.get('error')}: {result.get('details')}"
        )
    return result


def build_pypi_index(cache=None) -> PyPIIndex:
    from .pypi_cache import DbCacheStore
    from .resolver.index import LayeredCacheStore, MemoryCacheStore

    if cache is None:
        # The in-memory database's single shared connection can't take the
        # resolver's concurrent cache writes safely (see DatabaseDriverEnum).
        cache = (
            MemoryCacheStore()
            if settings.is_memory_db
            else LayeredCacheStore(DbCacheStore())
        )

    global pypi_client
    pypi_client = httpx.AsyncClient(
        timeout=settings.pypi_timeout_seconds,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=settings.pypi_max_connections),
        headers={
            "User-Agent": f"devsetgo-dsg/{__version__} (+https://github.com/devsetgo/dsg)"
        },
    )
    return PyPIIndex(
        pypi_client,
        cache,
        simple_url=settings.pypi_simple_url,
        json_url=settings.pypi_json_url,
        index_ttl=timedelta(seconds=settings.index_cache_ttl_seconds),
        version_info_ttl=timedelta(seconds=settings.version_info_cache_ttl_seconds),
    )


async def startup() -> None:
    global pypi_index
    logger.info("starting up services")
    if settings.is_memory_db:
        # Tests and throwaway dev runs: build the schema directly.
        await async_db.create_tables()
    else:
        # A file database's schema is owned by Alembic (entrypoint.sh runs
        # `alembic upgrade head` before the server starts).
        # Not db_ops.get_table_names(): that lists the models registered on
        # the metadata, not what exists in the database file.
        # read_query, not execute_one: execute_one doesn't recognize a raw
        # text() SELECT and returns the truthy string "complete" instead of rows.
        found = ensure_ok(
            await db_ops.read_query(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
                )
            )
        )
        if not found:
            raise RuntimeError(
                "Database is not migrated; run `alembic upgrade head` first."
            )
    pypi_index = build_pypi_index()

    from .checks import fail_stale_checks

    try:
        await fail_stale_checks()
    except RuntimeError as exc:
        # Housekeeping only: pages already treat stale checks as failed, and
        # this process must still serve requests.
        logger.warning(f"stale-check sweep skipped: {exc}")
    logger.info("startup complete")


async def shutdown() -> None:
    from .checks import cancel_checks

    logger.info("shutting down services")
    await cancel_checks()
    if pypi_client is not None:
        await pypi_client.aclose()
    if not settings.is_memory_db:
        try:
            await db_ops.execute_one(text("PRAGMA optimize"))
        except Exception as exc:  # pragma: no cover - best effort on the way out
            logger.warning(f"PRAGMA optimize failed: {exc}")
    await async_db.disconnect()
