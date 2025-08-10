# -*- coding: utf-8 -*-
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import tempfile
import os

from src.main import app

# Import individual tables instead of Base
from src.db_tables import Users, Notes, Posts, WebLinks, Categories
from src.resources import db_ops
from src.settings import settings

# Create Base for testing with the correct import
Base = declarative_base()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Create a test database."""
    # Use in-memory SQLite for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Create all tables
    async with engine.begin() as conn:
        # Import the metadata from the actual db_init or create minimal tables
        await conn.run_sync(lambda sync_conn: None)  # Skip table creation for now

    # Mock the db_ops to use test database
    original_engine = getattr(db_ops, "engine", None)
    if hasattr(db_ops, "engine"):
        db_ops.engine = engine

    yield engine

    # Restore original engine
    if original_engine and hasattr(db_ops, "engine"):
        db_ops.engine = original_engine
    await engine.dispose()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return {
        "pkid": "test-user-123",
        "user_name": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
        "is_admin": False,
        "my_timezone": "America/New_York",
        "roles": {"user_access": True, "notes": True, "posts": True},
        "date_created": "2024-01-01T00:00:00",
        "date_updated": "2024-01-01T00:00:00",
        "date_last_login": "2024-01-01T00:00:00",
        "failed_login_attempts": 0,
    }


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user for testing."""
    return {
        "pkid": "admin-user-123",
        "user_name": "adminuser",
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User",
        "is_active": True,
        "is_admin": True,
        "my_timezone": "America/New_York",
        "roles": {"user_access": True, "notes": True, "posts": True, "developer": True},
        "date_created": "2024-01-01T00:00:00",
        "date_updated": "2024-01-01T00:00:00",
        "date_last_login": "2024-01-01T00:00:00",
        "failed_login_attempts": 0,
    }


@pytest.fixture
def mock_note():
    """Create a mock note for testing."""
    return {
        "pkid": "note-123",
        "mood": "positive",
        "note": "This is a test note content.",
        "summary": "Test note",
        "tags": ["test", "note"],
        "mood_analysis": "happy",
        "user_id": "test-user-123",
        "ai_fix": False,
        "word_count": 6,
        "character_count": 30,
        "date_created": "2024-01-01T00:00:00",
        "date_updated": "2024-01-01T00:00:00",
    }


@pytest.fixture
def mock_post():
    """Create a mock post for testing."""
    return {
        "pkid": "post-123",
        "title": "Test Post",
        "summary": "This is a test post summary.",
        "content": "<p>This is test post content.</p>",
        "category": "technology",
        "tags": ["test", "post"],
        "user_id": "test-user-123",
        "date_created": "2024-01-01T00:00:00",
        "date_updated": "2024-01-01T00:00:00",
    }


@pytest.fixture
def mock_weblink():
    """Create a mock weblink for testing."""
    return {
        "pkid": "weblink-123",
        "title": "Test Website",
        "summary": "This is a test website summary.",
        "url": "https://example.com",
        "category": "technology",
        "public": True,
        "user_id": "test-user-123",
        "ai_fix": False,
        "image_preview_data": None,
        "comment": None,
        "date_created": "2024-01-01T00:00:00",
        "date_updated": "2024-01-01T00:00:00",
    }


@pytest.fixture
def mock_category():
    """Create a mock category for testing."""
    return {
        "pkid": "category-123",
        "name": "technology",
        "description": "Technology related content",
        "is_post": True,
        "is_weblink": True,
        "is_system": False,
        "date_created": "2024-01-01T00:00:00",
        "date_updated": "2024-01-01T00:00:00",
    }


@pytest.fixture
def mock_db_ops():
    """Mock database operations."""
    with patch("src.resources.db_ops") as mock_ops:
        # Configure common return values
        mock_ops.create_one = AsyncMock()
        mock_ops.read_one_record = AsyncMock()
        mock_ops.read_query = AsyncMock()
        mock_ops.update_one = AsyncMock()
        mock_ops.delete_one = AsyncMock()
        mock_ops.count_query = AsyncMock(return_value=0)
        yield mock_ops


@pytest.fixture
def mock_ai():
    """Mock AI functions."""
    with patch("src.functions.ai") as mock_ai_module:
        mock_ai_module.get_analysis = AsyncMock(
            return_value={
                "tags": {"tags": ["test", "sample"]},
                "summary": "Test summary",
                "mood_analysis": "happy",
                "mood": None,
            }
        )
        mock_ai_module.get_tags = AsyncMock(return_value={"tags": ["test", "sample"]})
        mock_ai_module.get_summary = AsyncMock(return_value="Test summary")
        mock_ai_module.get_mood = AsyncMock(return_value={"mood": "positive"})
        mock_ai_module.get_mood_analysis = AsyncMock(
            return_value={"mood_analysis": "happy"}
        )
        mock_ai_module.get_url_summary = AsyncMock(
            return_value={"summary": "Test URL summary"}
        )
        mock_ai_module.get_url_title = AsyncMock(return_value="Test URL Title")
        yield mock_ai_module


@pytest.fixture
def mock_background_tasks():
    """Mock background tasks."""
    with patch("fastapi.BackgroundTasks") as mock_tasks:
        mock_instance = MagicMock()
        mock_tasks.return_value = mock_instance
        yield mock_instance


# Helper function to mock database responses
def create_mock_db_record(data_dict):
    """Create a mock database record with to_dict method."""
    mock_record = MagicMock()
    mock_record.to_dict.return_value = data_dict
    # Add attributes for direct access
    for key, value in data_dict.items():
        setattr(mock_record, key, value)
    return mock_record


# Auth bypass fixture
@pytest.fixture
def bypass_auth():
    """Bypass authentication for testing."""

    # Mock the entire authentication dependency chain
    async def mock_check_login(request):
        # Set up request.state.user_info as the real function does
        request.state.user_info = {
            "user_identifier": "test-user-123",
            "timezone": "America/New_York",
            "is_admin": False,
            "exp": 9999999999,
        }
        return request.state.user_info

    # Mock check_user_identifier and check_session_expiry to prevent any auth issues
    async def mock_check_user_identifier(request):
        pass

    async def mock_check_session_expiry(request):
        pass

    # Create mock user data with all required fields
    mock_user_data = {
        "pkid": "test-user-123",
        "user_name": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
        "is_admin": False,
        "my_timezone": "America/New_York",
        "roles": {"user_access": True, "notes": True, "posts": True},
        "date_created": "2024-01-01T00:00:00",
        "date_updated": "2024-01-01T00:00:00",
        "date_last_login": "2024-01-01T00:00:00",
        "failed_login_attempts": 0,
    }

    # Create mock user record
    mock_user_record = create_mock_db_record(mock_user_data)

    # Mock get_user_name function to return a properly formatted name
    async def mock_get_user_name(user_id):
        return "Test User"

    # Patch all the authentication functions
    with patch(
        "src.functions.login_required.check_login", side_effect=mock_check_login
    ) as mock_login:
        with patch(
            "src.functions.login_required.check_user_identifier",
            side_effect=mock_check_user_identifier,
        ):
            with patch(
                "src.functions.login_required.check_session_expiry",
                side_effect=mock_check_session_expiry,
            ):
                # Mock db_ops.read_one_record for user lookups
                with patch(
                    "src.endpoints.blog_posts.db_ops.read_one_record",
                    AsyncMock(return_value=mock_user_record),
                ):
                    # Mock the get_user_name function to avoid the KeyError
                    with patch(
                        "src.endpoints.blog_posts.get_user_name",
                        side_effect=mock_get_user_name,
                    ):
                        # Also mock the dependency directly to ensure it returns the expected data
                        def mock_dependency():
                            return {
                                "user_identifier": "test-user-123",
                                "timezone": "America/New_York",
                                "is_admin": False,
                                "exp": 9999999999,
                            }

                        # Patch the dependency in the modules where it's used
                        with patch(
                            "src.endpoints.notes.check_login",
                            return_value=mock_dependency(),
                        ) as notes_dep:
                            with patch(
                                "src.endpoints.blog_posts.check_login",
                                return_value=mock_dependency(),
                            ) as posts_dep:
                                with patch(
                                    "src.endpoints.admin.check_login",
                                    return_value=mock_dependency(),
                                ) as admin_dep:
                                    yield


@pytest.fixture
def bypass_admin_auth():
    """Bypass authentication for admin testing."""

    # Mock the entire authentication dependency chain for admin
    async def mock_check_login(request):
        # Set up request.state.user_info as the real function does
        request.state.user_info = {
            "user_identifier": "admin-user-123",
            "timezone": "America/New_York",
            "is_admin": True,
            "exp": 9999999999,
        }
        return request.state.user_info

    # Mock check_user_identifier and check_session_expiry to prevent any auth issues
    async def mock_check_user_identifier(request):
        pass

    async def mock_check_session_expiry(request):
        pass

    # Patch all the authentication functions
    with patch(
        "src.functions.login_required.check_login", side_effect=mock_check_login
    ):
        with patch(
            "src.functions.login_required.check_user_identifier",
            side_effect=mock_check_user_identifier,
        ):
            with patch(
                "src.functions.login_required.check_session_expiry",
                side_effect=mock_check_session_expiry,
            ):
                # Also mock the dependency directly to ensure it returns the expected data
                def mock_dependency():
                    return {
                        "user_identifier": "admin-user-123",
                        "timezone": "America/New_York",
                        "is_admin": True,
                        "exp": 9999999999,
                    }

                # Patch the dependency in the modules where it's used
                with patch(
                    "src.endpoints.notes.check_login", return_value=mock_dependency()
                ):
                    with patch(
                        "src.endpoints.blog_posts.check_login",
                        return_value=mock_dependency(),
                    ):
                        with patch(
                            "src.endpoints.admin.check_login",
                            return_value=mock_dependency(),
                        ):
                            yield
