# -*- coding: utf-8 -*-
"""
SQLite-backed CacheStore for the resolver's PyPI responses, shared by every
worker process through the database file.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy import Select
from sqlalchemy.dialects.sqlite import insert

from .db_tables import PackageMetadataCache
from .resources import db_ops, ensure_ok


def _as_utc(value: datetime) -> datetime:
    # SQLite DateTime columns come back naive; they were written as UTC.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class DbCacheStore:
    async def get(self, key: str, max_age: timedelta | None) -> Any | None:
        row = await db_ops.read_one_record(
            Select(PackageMetadataCache).where(PackageMetadataCache.cache_key == key)
        )
        if row is None:
            return None
        if isinstance(row, dict):
            # A DatabaseErrorResult. Treat it as a miss so the check still
            # runs (from PyPI), but make a broken cache visible.
            logger.warning(f"cache read failed for {key}: {row.get('error')}")
            return None
        if (
            max_age is not None
            and datetime.now(timezone.utc) - _as_utc(row.fetched_at) > max_age
        ):
            return None
        return row.payload

    async def set(self, key: str, payload: Any) -> None:
        now = datetime.now(timezone.utc)
        statement = (
            insert(PackageMetadataCache)
            .values(cache_key=key, payload=payload, fetched_at=now)
            .on_conflict_do_update(
                index_elements=[PackageMetadataCache.cache_key],
                set_={"payload": payload, "fetched_at": now, "date_updated": now},
            )
        )
        try:
            ensure_ok(await db_ops.execute_one(statement))
        except RuntimeError as exc:
            # A cache write failing must not fail the check that triggered it.
            logger.warning(f"cache write failed for {key}: {exc}")
