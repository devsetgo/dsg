# -*- coding: utf-8 -*-

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_root():
    response = client.get("/pages/")
    assert response.status_code == 200
    assert response.url == "http://testserver/pages/index"


def test_index():
    url = "/pages/index"
    response = client.get(url)
    assert response.status_code == 200
    assert "<!DOCTYPE html >" in response.text


# /pypi/check
def test_pypi_check():
    url = "/pypi/check"
    response = client.get(url)
    assert response.status_code == 200
    assert "<!DOCTYPE html >" in response.text


# /pypi/index
def test_pypi_index():
    url = "/pypi/index"
    response = client.get(url)
    assert response.status_code == 200
    assert "<!DOCTYPE html >" in response.text


# /posts/
def test_posts():
    url = "/posts/"
    response = client.get(url)
    assert response.status_code == 200
    assert "<!DOCTYPE html >" in response.text


# /weblinks/
def test_weblinks():
    url = "/weblinks/"
    response = client.get(url)
    assert response.status_code == 200
    assert "<!DOCTYPE html >" in response.text


# /pages/about
def test_about():
    url = "/pages/about"
    response = client.get(url)
    assert response.status_code == 200
    assert "<!DOCTYPE html >" in response.text


# /pages/data
def test_data():
    url = "/pages/data"
    response = client.get(url)
    assert response.status_code == 200
    assert "<!DOCTYPE html >" in response.text
