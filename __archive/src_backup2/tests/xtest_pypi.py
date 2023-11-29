# -*- coding: utf-8 -*-

import uuid

import pytest

# from starlette.testclient import TestClient
from async_asgi_testclient import TestClient as Async_TestClient

from main import app


@pytest.mark.asyncio
async def test_pypi():
    async with Async_TestClient(app) as client:
        url = f"/pypi/check"
        response = await client.get(url)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_pypi_post():
    async with Async_TestClient(app) as client:
        url = f"/pypi/check"
        data = {"requirements": "flask"}
        response = await client.post(url, data=data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_pypi_error():
    client = Async_TestClient(app)
    uid = uuid.uuid1()
    url = f"/pypi/{uid}"
    response = await client.get(url)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pypi_dashboard():
    async with Async_TestClient(app) as client:
        url = f"/pypi/dashboard"
        response = await client.get(url)
        assert response.status_code == 200
