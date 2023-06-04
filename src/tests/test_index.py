# -*- coding: utf-8 -*-
import unittest

from starlette.testclient import TestClient

from main import app

client = TestClient(app)


class TestTopLevel(unittest.TestCase):
    async def test_index(self):
        url = f"/index"

        with client:
            response = await client.get(url)
            assert response.status_code == 200

    async def test_about(self):
        url = f"/about"

        with client:
            response = await client.get(url)
            assert response.status_code == 200

    async def test_health(self):
        url = f"/health"

        with client:
            response = await client.get(url)
            assert response.status_code == 200
