# -*- coding: utf-8 -*-
"""
Comprehensive tests for the devtools.py module.

This module provides complete test coverage for all devtools functionality including:
- POST /devtools/pypi/check-list endpoint for checking multiple packages
- GET /devtools/pypi/check-one endpoint for checking a single package
- Error handling for both endpoints
- Logging functionality
- UUID generation
- Integration with pypi_core.check_packages function
- JSONResponse formatting
- Exception handling and HTTPException raising

Target: 85% coverage (currently at 37%)
"""

import pytest
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.responses import JSONResponse


class TestDevtoolsCore:
    """Test core devtools functionality."""

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_post_check_pypi_packages_success(
        self, mock_logger, mock_check_packages, client
    ):
        """Test successful POST request to check multiple packages."""
        # Mock the check_packages function to return sample data
        mock_package_data = [
            {
                "name": "requests",
                "version": "2.31.0",
                "description": "HTTP library for Python",
                "home_page": "https://requests.readthedocs.io",
                "author": "Kenneth Reitz",
            },
            {
                "name": "fastapi",
                "version": "0.104.1",
                "description": "FastAPI framework, high performance, easy to learn",
                "home_page": "https://github.com/tiangolo/fastapi",
                "author": "Sebastián Ramírez",
            },
        ]
        mock_check_packages.return_value = mock_package_data

        # Test data
        test_packages = ["requests", "fastapi"]

        # Make the POST request
        response = client.post(
            "/devtools/pypi/check-list",
            json=test_packages,
            headers={"Content-Type": "application/json"},
        )

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, list)
        assert len(response_data) == 2
        assert response_data[0]["name"] == "requests"
        assert response_data[1]["name"] == "fastapi"

        # Verify that check_packages was called with correct arguments
        mock_check_packages.assert_called_once()
        call_args = mock_check_packages.call_args
        assert call_args[1]["packages"] == test_packages
        assert call_args[1]["request"] is None
        assert "request_group_id" in call_args[1]

        # Verify logging was called
        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 2  # Start and success logs

        # Check that UUID was generated (should be a valid UUID string)
        uuid_arg = call_args[1]["request_group_id"]
        assert isinstance(uuid_arg, str)
        uuid.UUID(uuid_arg)  # Will raise ValueError if not valid UUID

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_post_check_pypi_packages_single_package(
        self, mock_logger, mock_check_packages, client
    ):
        """Test POST request with single package."""
        mock_package_data = [
            {
                "name": "numpy",
                "version": "1.24.3",
                "description": "Fundamental package for array computing with Python",
            }
        ]
        mock_check_packages.return_value = mock_package_data

        test_packages = ["numpy"]

        response = client.post(
            "/devtools/pypi/check-list",
            json=test_packages,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]["name"] == "numpy"

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_post_check_pypi_packages_empty_list(
        self, mock_logger, mock_check_packages, client
    ):
        """Test POST request with empty package list."""
        mock_check_packages.return_value = []

        response = client.post(
            "/devtools/pypi/check-list",
            json=[],
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, list)
        assert len(response_data) == 0

        mock_check_packages.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_post_check_pypi_packages_exception_handling(
        self, mock_logger, mock_check_packages, client
    ):
        """Test exception handling in POST endpoint."""
        # Mock check_packages to raise an exception
        mock_check_packages.side_effect = Exception("PyPI service unavailable")

        test_packages = ["requests"]

        # The exception will result in HTTPException being raised
        # which the test client will catch and follow redirects
        with pytest.raises(Exception):
            response = client.post(
                "/devtools/pypi/check-list",
                json=test_packages,
                headers={"Content-Type": "application/json"},
            )

        # Verify the check_packages was called with correct parameters
        mock_check_packages.assert_called_once()
        call_args = mock_check_packages.call_args
        assert call_args[1]["packages"] == test_packages
        assert "request_group_id" in call_args[1]
        """Test exception handling in POST endpoint."""
        # Mock check_packages to raise an exception
        mock_check_packages.side_effect = Exception("PyPI service unavailable")

        test_packages = ["requests"]

        response = client.post(
            "/devtools/pypi/check-list",
            json=test_packages,
            headers={"Content-Type": "application/json"},
        )

        # Should return 500 with error message
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to check packages"

        # Verify error logging
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to check packages" in error_call
        assert "PyPI service unavailable" in error_call

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_get_check_pypi_packages_success(
        self, mock_logger, mock_check_packages, client
    ):
        """Test successful GET request to check single package."""
        mock_package_data = [
            {
                "name": "django",
                "version": "4.2.7",
                "description": "A high-level Python web framework",
                "home_page": "https://www.djangoproject.com/",
                "author": "Django Software Foundation",
            }
        ]
        mock_check_packages.return_value = mock_package_data

        response = client.get("/devtools/pypi/check-one?package=django")

        assert response.status_code == 200
        response_data = response.json()

        # Should return the first (and only) item from the list, not the list itself
        assert isinstance(response_data, dict)
        assert response_data["name"] == "django"
        assert response_data["version"] == "4.2.7"

        # Verify check_packages was called correctly
        mock_check_packages.assert_called_once()
        call_args = mock_check_packages.call_args
        assert call_args[0] == (["django"],)  # packages parameter
        assert call_args[1]["request"] is None
        assert "request_group_id" in call_args[1]

        # Verify logging
        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 2  # Start and success logs

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_get_check_pypi_packages_with_special_characters(
        self, mock_logger, mock_check_packages, client
    ):
        """Test GET request with package name containing special characters."""
        mock_package_data = [
            {
                "name": "python-dateutil",
                "version": "2.8.2",
                "description": "Extensions to the standard Python datetime module",
            }
        ]
        mock_check_packages.return_value = mock_package_data

        response = client.get("/devtools/pypi/check-one?package=python-dateutil")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == "python-dateutil"

        # Verify the package was wrapped in a list for check_packages
        call_args = mock_check_packages.call_args
        assert call_args[0] == (["python-dateutil"],)

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_get_check_pypi_packages_exception_handling(
        self, mock_logger, mock_check_packages, client
    ):
        """Test exception handling in GET endpoint."""
        # Mock check_packages to raise an exception
        mock_check_packages.side_effect = ConnectionError("Network error")

        response = client.get("/devtools/pypi/check-one?package=requests")

        # Should return 500 with error message
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to check package"

        # Verify error logging
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to check package" in error_call
        assert "Network error" in error_call

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_get_check_pypi_packages_missing_parameter(
        self, mock_logger, mock_check_packages, client
    ):
        """Test GET request without package parameter."""
        response = client.get("/devtools/pypi/check-one")

        # FastAPI should return 422 for missing required parameter
        assert response.status_code == 422

        # check_packages should not be called
        mock_check_packages.assert_not_called()


class TestDevtoolsLogging:
    """Test logging functionality in devtools endpoints."""

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_logging_post_endpoint(
        self, mock_logger, mock_check_packages, client
    ):
        """Test that logging works correctly for POST endpoint."""
        mock_check_packages.return_value = [{"name": "test", "version": "1.0"}]

        test_packages = ["test-package"]

        response = client.post(
            "/devtools/pypi/check-list",
            json=test_packages,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200

        # Verify info logging calls
        assert mock_logger.info.call_count == 2

        # Check the log messages
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Checking packages:" in log for log in log_calls)
        assert any("Successfully checked packages:" in log for log in log_calls)

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_logging_get_endpoint(self, mock_logger, mock_check_packages, client):
        """Test that logging works correctly for GET endpoint."""
        mock_check_packages.return_value = [{"name": "test", "version": "1.0"}]

        response = client.get("/devtools/pypi/check-one?package=test-package")

        assert response.status_code == 200

        # Verify info logging calls
        assert mock_logger.info.call_count == 2

        # Check the log messages
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Checking package:" in log for log in log_calls)
        assert any("Successfully checked package:" in log for log in log_calls)

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_error_logging_post(self, mock_logger, mock_check_packages, client):
        """Test error logging for POST endpoint."""
        error_message = "Database connection failed"
        mock_check_packages.side_effect = Exception(error_message)

        response = client.post(
            "/devtools/pypi/check-list",
            json=["test"],
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 500

        # Verify error logging
        mock_logger.error.assert_called_once()
        error_log = mock_logger.error.call_args[0][0]
        assert "Failed to check packages" in error_log
        assert error_message in error_log

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("src.endpoints.devtools.logger")
    async def test_error_logging_get(self, mock_logger, mock_check_packages, client):
        """Test error logging for GET endpoint."""
        error_message = "API rate limit exceeded"
        mock_check_packages.side_effect = Exception(error_message)

        response = client.get("/devtools/pypi/check-one?package=test")

        assert response.status_code == 500

        # Verify error logging
        mock_logger.error.assert_called_once()
        error_log = mock_logger.error.call_args[0][0]
        assert "Failed to check package" in error_log
        assert error_message in error_log


class TestDevtoolsIntegration:
    """Test integration aspects of devtools endpoints."""

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    async def test_uuid_generation_uniqueness(self, mock_check_packages, client):
        """Test that each request generates a unique UUID."""
        mock_check_packages.return_value = []

        # Make multiple requests
        client.post("/devtools/pypi/check-list", json=["test1"])
        client.post("/devtools/pypi/check-list", json=["test2"])
        client.get("/devtools/pypi/check-one?package=test3")

        # Get all the UUID calls
        calls = mock_check_packages.call_args_list
        assert len(calls) == 3

        uuids = [call[1]["request_group_id"] for call in calls]

        # All UUIDs should be unique
        assert len(set(uuids)) == 3

        # All should be valid UUIDs
        for uuid_str in uuids:
            uuid.UUID(uuid_str)  # Will raise if invalid

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    async def test_request_parameter_handling(self, mock_check_packages, client):
        """Test that request parameter is properly handled (should be None)."""
        mock_check_packages.return_value = []

        client.post("/devtools/pypi/check-list", json=["test"])

        call_args = mock_check_packages.call_args
        assert call_args[1]["request"] is None

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    async def test_json_response_formatting(self, mock_check_packages, client):
        """Test that responses are properly formatted as JSON."""
        mock_data = [{"name": "test", "version": "1.0", "complex": {"nested": "data"}}]
        mock_check_packages.return_value = mock_data

        # Test POST endpoint
        post_response = client.post("/devtools/pypi/check-list", json=["test"])
        assert post_response.headers["content-type"] == "application/json"
        assert post_response.json() == mock_data

        # Test GET endpoint
        get_response = client.get("/devtools/pypi/check-one?package=test")
        assert get_response.headers["content-type"] == "application/json"
        assert get_response.json() == mock_data[0]  # Should return first item


class TestDevtoolsEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    async def test_large_package_list(self, mock_check_packages, client):
        """Test handling of large package lists."""
        # Create a large list of package names
        large_list = [f"package-{i}" for i in range(100)]
        mock_check_packages.return_value = [
            {"name": f"package-{i}", "version": "1.0"} for i in range(100)
        ]

        response = client.post(
            "/devtools/pypi/check-list",
            json=large_list,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert len(response.json()) == 100

        # Verify the call was made with all packages
        call_args = mock_check_packages.call_args
        assert len(call_args[1]["packages"]) == 100

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    async def test_special_package_names(self, mock_check_packages, client):
        """Test handling of packages with special names."""
        special_packages = [
            "package-with-dashes",
            "package_with_underscores",
            "Package.With.Dots",
            "UPPERCASE-PACKAGE",
            "123numeric-start",
        ]

        mock_data = [{"name": pkg, "version": "1.0"} for pkg in special_packages]
        mock_check_packages.return_value = mock_data

        response = client.post(
            "/devtools/pypi/check-list",
            json=special_packages,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 5

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    async def test_none_return_handling(self, mock_check_packages, client):
        """Test handling when check_packages returns None or empty data."""
        mock_check_packages.return_value = None

        response = client.post("/devtools/pypi/check-list", json=["test"])

        # Should still return 200 but with None data
        assert response.status_code == 200
        assert response.json() is None

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    async def test_get_endpoint_array_index_handling(self, mock_check_packages, client):
        """Test GET endpoint behavior when check_packages returns empty list."""
        mock_check_packages.return_value = []

        # This should cause an IndexError when trying to access data[0]
        response = client.get("/devtools/pypi/check-one?package=nonexistent")

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to check package"


class TestDevtoolsPrintStatements:
    """Test the print statements in the devtools module."""

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("builtins.print")
    async def test_get_endpoint_print_statement(
        self, mock_print, mock_check_packages, client
    ):
        """Test that the print statement is executed in the GET endpoint."""
        mock_check_packages.return_value = [{"name": "test", "version": "1.0"}]

        response = client.get("/devtools/pypi/check-one?package=test-package")

        assert response.status_code == 200

        # Verify print was called with the package name
        mock_print.assert_called_once_with("test-package")

    @pytest.mark.asyncio
    @patch("src.endpoints.devtools.check_packages")
    @patch("builtins.print")
    async def test_post_endpoint_print_statement(
        self, mock_print, mock_check_packages, client
    ):
        """Test that the print statement is executed in the POST endpoint for exceptions."""
        error = Exception("Test error")
        mock_check_packages.side_effect = error

        response = client.post(
            "/devtools/pypi/check-list",
            json=["test"],
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 500

        # Verify print was called with the exception
        mock_print.assert_called_once_with(error)


class TestDevtoolsRouter:
    """Test router configuration and endpoint registration."""

    def test_router_exists(self):
        """Test that the router is properly configured."""
        from src.endpoints.devtools import router
        from fastapi import APIRouter

        assert isinstance(router, APIRouter)

        # Check that routes are registered
        routes = router.routes
        assert len(routes) >= 2  # Should have at least 2 routes

        # Check route paths and methods
        route_info = [(route.path, route.methods) for route in routes]

        # Should contain our two endpoints
        post_route_found = any(
            path == "/pypi/check-list" and "POST" in methods
            for path, methods in route_info
        )
        get_route_found = any(
            path == "/pypi/check-one" and "GET" in methods
            for path, methods in route_info
        )

        assert post_route_found, "POST /pypi/check-list route not found"
        assert get_route_found, "GET /pypi/check-one route not found"

    def test_imports(self):
        """Test that all required imports are available."""
        # Test individual imports
        import uuid
        from typing import List
        from fastapi import APIRouter, Body, HTTPException
        from fastapi.responses import JSONResponse
        from loguru import logger

        # Test the specific import from src.functions.pypi_core
        from src.functions.pypi_core import check_packages

        # All imports should work without raising ImportError
        assert uuid is not None
        assert List is not None
        assert APIRouter is not None
        assert Body is not None
        assert HTTPException is not None
        assert JSONResponse is not None
        assert logger is not None
        assert check_packages is not None
