# -*- coding: utf-8 -*-
import unittest
from starlette.testclient import TestClient
from main import app

client = TestClient(app)


class TestPyPiData(unittest.TestCase):
    async def test_pypi_data(self):
        url = "/pypi/dashboard"
        with client:
            response = await client.get(url)
            self.assertEqual(response.status_code, 200)
            .....

            # Check if the returned template is correct
            self.assertIn(b"pypi/dashboard.html", await response.content.read())

            # Check if the returned data contains the expected keys
            data = response.context["data"]
            self.assertIn("req_data", data)
            self.assertIn("lib_data", data)
            self.assertIn("latest_results", data)

