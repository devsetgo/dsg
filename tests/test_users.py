# -*- coding: utf-8 -*-
# FILE: test_users.py
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app, follow_redirects=True)


def test_login(test_client, mock_login):
    response = test_client.get("/users/user-info")
    assert response.status_code == 200
    assert (
        "<!DOCTYPE html>" in response.text
    )  # Check for a specific text in the HTML response
