# -*- coding: utf-8 -*-
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_root():
    response = client.get("/pages/")
    assert response.status_code == 200
    assert response.url == "http://testserver/pages/index"


def test_index():
    response = client.get("/pages/index")
    assert response.status_code == 200
    assert "<!DOCTYPE html >" in response.text


# @patch("src.main.pypi.get_check_form")
# def test_get_check_form(mock_get_check_form):
#     mock_get_check_form.return_value = {
#         "csrf_token": "test",
#         "request_group_id": "test",
#     }
#     response = client.get("/pages/check")
#     assert response.status_code == 200
#     assert "pypi/new.html" in response.text


# @patch("src.main.pypi.post_check_form")
# def test_post_check_form(mock_post_check_form):
#     mock_post_check_form.return_value = {"request_group_id": "test"}
#     response = client.post("/pages/check")
#     assert response.status_code == 303
#     assert response.url == "/pypi/check/test"


# @patch("src.main.pypi.get_response")
# def test_get_response(mock_get_response):
#     mock_get_response.return_value = {"request_group_id": "test"}
#     response = client.get("/pages/check/test")
#     assert response.status_code == 200
#     assert "pypi/result.html" in response.text


# @patch("src.main.pypi.get_all")
# def test_get_all(mock_get_all):
#     mock_get_all.return_value = {"db_data": [], "count_data": 0}
#     response = client.get("/pages/list")
#     assert response.status_code == 200
#     assert "pypi/simple-list.html" in response.text
