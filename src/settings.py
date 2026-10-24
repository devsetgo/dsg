# -*- coding: utf-8 -*-
"""
Application settings, loaded from environment variables / `.env` by
pydantic-settings and cached for the life of the process.

The app is a single-purpose, public PyPI dependency resolver backed by SQLite,
so this holds only database, logging, server and resolver configuration.

Author:
    Mike Ryan

License:
    MIT License
"""

from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from . import __version__


class DatabaseDriverEnum(str, Enum):
    sqlite = "sqlite+aiosqlite"
    # Test-only. SQLAlchemy serves :memory: through a StaticPool - one
    # connection shared by every session - so concurrent sessions interleave
    # their transactions and one's ROLLBACK can silently discard another's
    # INSERT. Fine for the test suite's sequential requests; use a file for
    # anything that serves real traffic (even locally).
    memory = "sqlite+aiosqlite:///:memory:"


class Settings(BaseSettings):
    # database
    # The enum member, not "sqlite": pydantic-settings validates defaults, and
    # parse_database_driver only maps the short names it is given.
    db_driver: DatabaseDriverEnum = Field(
        DatabaseDriverEnum.sqlite, description="sqlite (file) or memory (tests)"
    )
    db_directory: str = Field("sqlite_db", description="Folder holding the SQLite file")
    db_name: str = Field("dsg", description="SQLite file name; '.db' is appended")
    # Off unless asked for: echo logs every statement with its bound parameters.
    echo: bool = False
    future: bool = True
    pool_recycle: int = 3600
    # Robyn runs several worker processes against one file, and writes are
    # serialized across them - wait for the lock instead of failing.
    sqlite_busy_timeout_ms: int = 5000
    # Negative = KiB, per connection.
    sqlite_cache_size_kib: int = 65536
    # An upper bound, not an allocation - only the file's actual size is mapped.
    sqlite_mmap_size_bytes: int = 268435456

    # application
    date_run: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = __version__
    debug_mode: bool = False

    # server
    host: str = "0.0.0.0"
    port: int = 5000

    # logging
    logging_directory: str = "log"
    log_name: str = "log"
    logging_level: str = "INFO"
    log_rotation: str = "100 MB"
    log_retention: str = "30 days"
    log_backtrace: bool = False
    log_serializer: bool = False
    log_diagnose: bool = False
    log_intercept_standard_logging: bool = False
    # Per-request access log from the app (Traefik already logs access in production).
    access_log: bool = False

    # resolver
    pypi_simple_url: str = "https://pypi.org/simple"
    pypi_json_url: str = "https://pypi.org/pypi"
    pypi_timeout_seconds: float = 30.0
    pypi_max_connections: int = 32
    # Index pages change whenever a release is uploaded; a released file's
    # metadata never changes, so it is cached without expiry.
    index_cache_ttl_seconds: int = 3600
    # Vulnerability reports are added to old releases over time.
    version_info_cache_ttl_seconds: int = 86400
    check_timeout_seconds: int = 180
    # Per process: resolutions run at once, and how many more may wait before
    # new submissions get "busy, try again" (HTTP 429).
    max_concurrent_checks: int = 4
    max_queued_checks: int = 20
    # Per client IP per process, for POST /check and /api/check; 0 disables.
    checks_per_minute_per_ip: int = 10
    # Reverse proxies in front of the app (Traefik = 1). The client address is
    # taken that many entries from the right of X-Forwarded-For, since each
    # proxy appends the peer it saw and everything further left is whatever
    # the client sent. 0: ignore the header and use the socket peer.
    forwarded_proxy_hops: int = 1
    # List every check on /history. Off: results are reachable only through
    # their (unguessable) link, since a pasted file can name private packages.
    public_history: bool = False
    resolver_max_rounds: int = 2000
    max_requirement_lines: int = 100
    default_python_version: str = "3.14"

    # health endpoints
    health_status_endpoint: bool = True
    health_uptime_endpoint: bool = True

    @property
    def is_memory_db(self) -> bool:
        """True for the throwaway in-memory database the test suite uses. Its
        schema comes from create_tables() on boot; a file database's comes
        from Alembic (see resources.startup)."""
        return self.db_driver == DatabaseDriverEnum.memory

    @model_validator(mode="before")
    @classmethod
    def parse_database_driver(cls, values):
        db_driver = values.get("db_driver")
        if (
            isinstance(db_driver, str)
            and db_driver.lower() in DatabaseDriverEnum.__members__
        ):
            values["db_driver"] = DatabaseDriverEnum[db_driver.lower()]
        return values

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # .env files on dev machines still carry settings from the pre-Robyn app.
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    # No settings dump here: this runs at import, before logging_config sets
    # the level, so loguru's default DEBUG handler would print it every start.
    return Settings()


settings = get_settings()
