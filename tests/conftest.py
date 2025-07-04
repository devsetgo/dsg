# -*- coding: utf-8 -*-
# FILE: conftest.py
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.db_tables import Users
from src.main import app
from src.resources import db_ops


@pytest.fixture(scope="module")
def test_client():
    client = TestClient(app)
    yield client


@pytest.fixture(scope="module")
async def mock_user():
    # Create a mock user in the database
    user_data = {
        "user_name": "testuser",
        "email": "testuser@example.com",
        "my_timezone": "UTC",
        "is_active": True,
        "is_admin": False,
        "roles": {"user_access": True},
    }
    user = Users(**user_data)
    await db_ops.create_one(user)
    yield user
    # Clean up the mock user from the database
    await db_ops.delete_one(Users, user.pkid)


@pytest.fixture(scope="module")
async def mock_login(test_client, mock_user):
    # Mock the login process by setting cookies
    session_data = {
        "user_identifier": mock_user.pkid,
        "roles": mock_user.roles,
        "is_active": mock_user.is_active,
        "is_admin": mock_user.is_admin,
        "timezone": mock_user.my_timezone,
        "exp": (datetime.now() + timedelta(minutes=30)).timestamp(),
    }
    test_client.cookies.set("session", json.dumps(session_data))
    yield
