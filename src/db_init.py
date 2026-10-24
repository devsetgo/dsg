# -*- coding: utf-8 -*-
"""
Initializes the SQLite database connection: a single file under
`settings.db_directory` (a Docker volume in production), or a throwaway
in-memory database (`DB_DRIVER=memory`, what the test suite uses).

Author:
    Mike Ryan

License:
    MIT License
"""

import os

from dsg_lib.async_database_functions import async_database, database_config
from loguru import logger
from sqlalchemy import event

from .settings import DatabaseDriverEnum, settings

SQLITE_AIOSQLITE_DRIVER = "sqlite+aiosqlite"

if settings.db_driver == DatabaseDriverEnum.memory:  # pragma: no cover
    db_uri: str = settings.db_driver.value
    db_path: str | None = None
else:  # pragma: no cover
    db_name = settings.db_name if "." in settings.db_name else f"{settings.db_name}.db"
    db_path = os.path.join(settings.db_directory, db_name)
    # SQLite creates the file but not its folder - a missing folder surfaces as
    # a confusing "unable to open database file" at the first query otherwise.
    os.makedirs(settings.db_directory, exist_ok=True)
    db_uri = f"{SQLITE_AIOSQLITE_DRIVER}:///{db_path}"
logger.debug(f"database uri: {db_uri}")

config = {
    "database_uri": db_uri,
    "echo": settings.echo,
    "future": settings.future,
    "pool_recycle": settings.pool_recycle,
}
db_config = database_config.DBConfig(config)
async_db = async_database.AsyncDatabase(db_config)


@event.listens_for(db_config.engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record):
    """
    Per-connection SQLite tuning. PRAGMAs other than journal_mode don't persist
    in the file, so they are re-applied on every connection the pool opens.

    - journal_mode=WAL: readers never block the writer, which matters because
      every Robyn worker process polls check status from the same file.
      Skipped for :memory:, which can't use WAL.
    - synchronous=NORMAL: safe under WAL and avoids an fsync on every commit.
    - busy_timeout: wait for another process's write lock instead of failing
      immediately with "database is locked".
    - foreign_keys: SQLite ignores FOREIGN KEY constraints unless asked.
    """
    cursor = dbapi_connection.cursor()
    try:
        # First, so it also covers the journal_mode switch below: on a fresh
        # file every Robyn process connects at once, and without a timeout
        # the losers of that race fail with "database is locked".
        cursor.execute(f"PRAGMA busy_timeout={int(settings.sqlite_busy_timeout_ms)}")
        if db_path is not None:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA mmap_size={int(settings.sqlite_mmap_size_bytes)}")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA temp_store=MEMORY")
        # Negative means KiB; a positive value would be a page count.
        cursor.execute(f"PRAGMA cache_size=-{int(settings.sqlite_cache_size_kib)}")
    finally:
        cursor.close()
