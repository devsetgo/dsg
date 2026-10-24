# -*- coding: utf-8 -*-
"""Against the real PyPI. Skipped by default; run with `pytest -m network`."""

import httpx
import pytest

from src.resolver.environment import TargetEnvironment
from src.resolver.index import MemoryCacheStore, PyPIIndex
from src.resolver.service import resolve_requirements

pytestmark = pytest.mark.network


async def resolve_live(text: str, python: str, mode: str = "upgrade"):
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        index = PyPIIndex(client, MemoryCacheStore())
        return await resolve_requirements(
            text, index=index, target=TargetEnvironment(python), mode=mode
        )


async def test_numpy_respects_requires_python():
    old = await resolve_live("numpy", "3.10")
    new = await resolve_live("numpy", "3.14")
    old_numpy = old.packages[0]
    assert old.ok and new.ok
    # numpy 2.3 dropped 3.10; whatever the newest release is, 3.10 can't have it.
    assert old_numpy.resolved_version.startswith("2.2.")
    assert old_numpy.latest_version != old_numpy.resolved_version
    assert new.packages[0].resolved_version == new.packages[0].latest_version


async def test_real_conflict_is_explained():
    report = await resolve_live(
        "pydantic==1.10.0\npydantic-settings>=2", "3.12", mode="validate"
    )
    assert not report.ok
    assert report.conflicts[0].package == "pydantic"


async def test_extras_resolve():
    report = await resolve_live("fastapi[standard]", "3.12")
    assert report.ok
    names = {p.name for p in report.packages}
    assert {"fastapi", "uvicorn", "httpx", "jinja2"} <= names
