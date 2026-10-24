# -*- coding: utf-8 -*-
import os
import tempfile

# Settings are read once at import, so these must be set before anything
# imports src.
os.environ["DB_DRIVER"] = "memory"
os.environ["LOGGING_LEVEL"] = "WARNING"
# Keep test runs (and their expected warnings) out of the app's real log.
os.environ["LOGGING_DIRECTORY"] = tempfile.mkdtemp(prefix="dsg-test-logs-")

import pytest  # noqa: E402

from src.resolver.environment import TargetEnvironment  # noqa: E402
from src.resolver.index import MemoryCacheStore, PyPIIndex  # noqa: E402
from src.resolver.service import resolve_requirements  # noqa: E402
from src.settings import settings  # noqa: E402
from tests.fakepypi import JSON, SIMPLE, FakePyPI  # noqa: E402

assert settings.is_memory_db, "tests must never touch a real database file"


def make_index(fake: FakePyPI) -> PyPIIndex:
    return PyPIIndex(
        fake.client(), MemoryCacheStore(), simple_url=SIMPLE, json_url=JSON
    )


@pytest.fixture
def resolve():
    """resolve(spec, text, python="3.12", mode="upgrade", platform="linux-x86_64") -> (report, fake)"""

    async def _resolve(
        spec, text, python="3.12", mode="upgrade", platform="linux-x86_64", **kwargs
    ):
        fake = FakePyPI(spec)
        index = make_index(fake)
        try:
            report = await resolve_requirements(
                text,
                index=index,
                target=TargetEnvironment(python, platform),
                mode=mode,
                **kwargs,
            )
        finally:
            await index.client.aclose()
        return report, fake

    return _resolve


@pytest.fixture
def logged():
    """Messages loguru emits at WARNING and above during the test."""
    from loguru import logger

    messages: list[str] = []
    sink = logger.add(lambda m: messages.append(m.record["message"]), level="WARNING")
    yield messages
    logger.remove(sink)
