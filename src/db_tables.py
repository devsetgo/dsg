# -*- coding: utf-8 -*-
"""
SQLAlchemy models for the package resolver.

- Check: one submitted requirements file and its resolution report.
- CheckPackage: one row per package in a finished report, kept separately from
  the report JSON so the stats page can aggregate with SQL.
- PackageMetadataCache: PyPI responses cached across checks (see
  resolver.cache).

Author:
    Mike Ryan

License:
    MIT License
"""

from dsg_lib.async_database_functions import base_schema
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .db_init import async_db


class CheckStatus:
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"

    finished = (done, failed)


class Check(base_schema.SchemaBaseSQLite, async_db.Base):
    __tablename__ = "checks"
    __table_args__ = {"comment": "A submitted requirements file and its resolution"}

    request_group_id = Column(String(36), unique=True, index=True, nullable=False)
    status = Column(String(16), default=CheckStatus.pending, index=True, nullable=False)
    target_python = Column(String(8), index=True, nullable=False)
    platform = Column(String(32), nullable=False)
    mode = Column(String(16), nullable=False)
    text_in = Column(Text, nullable=False)
    lib_in_count = Column(Integer, default=0)
    lib_out_count = Column(Integer, default=0)
    resolved_requirements = Column(Text)
    locked_requirements = Column(Text)
    # True when the report has at least one conflict (resolution failed).
    has_conflicts = Column(Boolean, default=False, index=True)
    report = Column(JSON)
    error = Column(Text)
    duration_ms = Column(Integer)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    host_ip = Column(String(64), index=True)
    user_agent = Column(String(512))

    packages = relationship(
        "CheckPackage", back_populates="check", cascade="all, delete-orphan"
    )


class CheckPackage(base_schema.SchemaBaseSQLite, async_db.Base):
    __tablename__ = "check_packages"
    __table_args__ = {"comment": "One package of a finished check"}

    check_id = Column(
        String(36), ForeignKey("checks.pkid", ondelete="CASCADE"), index=True
    )
    name = Column(String(256), index=True, nullable=False)
    extras = Column(String(256))
    input_spec = Column(String(512))
    current_version = Column(String(64))
    latest_version = Column(String(64))
    latest_compatible = Column(String(64))
    resolved_version = Column(String(64))
    is_direct = Column(Boolean, default=True, index=True)
    is_held_back = Column(Boolean, default=False, index=True)
    held_back_by = Column(JSON)
    vulnerability_count = Column(Integer, default=0)
    vulnerabilities = Column(JSON)

    check = relationship("Check", back_populates="packages")


class PackageMetadataCache(base_schema.SchemaBaseSQLite, async_db.Base):
    __tablename__ = "package_metadata_cache"
    __table_args__ = {"comment": "PyPI responses cached across checks"}

    cache_key = Column(String(512), unique=True, index=True, nullable=False)
    payload = Column(JSON)
    fetched_at = Column(DateTime, nullable=False)
