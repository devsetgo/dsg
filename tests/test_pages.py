# -*- coding: utf-8 -*-

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
