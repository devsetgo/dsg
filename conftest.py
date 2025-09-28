# -*- coding: utf-8 -*-
import pytest
import asyncio
from tests.conftest import *  # Import all fixtures from tests/conftest.py


# Configure asyncio for pytest
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Enable asyncio mode
pytest_plugins = ("pytest_asyncio",)
