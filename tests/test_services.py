# -*- coding: utf-8 -*-
"""
Comprehensive tests for services.py module focusing on categories endpoint.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import Select

from src.endpoints.services import router, cat_list
from src.db_tables import Categories


@pytest.fixture
def client():
    """Create a test client for the services router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/services")
    return TestClient(app)


@pytest.fixture
def mock_category():
    """Create a mock category object with to_dict method."""
    mock_cat = MagicMock()
    mock_cat.to_dict.return_value = {"name": "test-category"}
    return mock_cat


@pytest.fixture
def multiple_mock_categories():
    """Create multiple mock category objects."""
    categories = []
    for i, name in enumerate(["category-1", "category-2", "category-3"]):
        mock_cat = MagicMock()
        mock_cat.to_dict.return_value = {"name": name}
        categories.append(mock_cat)
    return categories


class TestServicesGetCategories:
    """Test the get_categories endpoint with various scenarios."""

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_get_categories_no_filter_success(
        self, mock_logger, mock_db_read, client, multiple_mock_categories
    ):
        """Test successful retrieval of all categories without filter."""
        mock_db_read.return_value = multiple_mock_categories

        response = client.get("/services/categories")

        assert response.status_code == 200
        data = response.json()
        assert data == ["category-1", "category-2", "category-3"]

        # Verify db_ops.read_query was called with correct parameters
        mock_db_read.assert_called_once()
        call_args = mock_db_read.call_args[0]
        assert isinstance(call_args[0], Select)

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_get_categories_with_filter_success(
        self, mock_logger, mock_db_read, client, mock_category
    ):
        """Test successful retrieval of categories with category_name filter."""
        mock_db_read.return_value = [mock_category]

        response = client.get("/services/categories?category_name=is_post")

        assert response.status_code == 200
        data = response.json()
        assert data == ["test-category"]

        # Verify db_ops.read_query was called
        mock_db_read.assert_called_once()
        call_args = mock_db_read.call_args[0]
        assert isinstance(call_args[0], Select)

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_get_categories_with_weblink_filter(
        self, mock_logger, mock_db_read, client, mock_category
    ):
        """Test retrieval with is_weblink filter."""
        mock_db_read.return_value = [mock_category]

        response = client.get("/services/categories?category_name=is_weblink")

        assert response.status_code == 200
        data = response.json()
        assert data == ["test-category"]
        mock_db_read.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_get_categories_with_system_filter(
        self, mock_logger, mock_db_read, client, mock_category
    ):
        """Test retrieval with is_system filter."""
        mock_db_read.return_value = [mock_category]

        response = client.get("/services/categories?category_name=is_system")

        assert response.status_code == 200
        data = response.json()
        assert data == ["test-category"]
        mock_db_read.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_get_categories_empty_result(self, mock_logger, mock_db_read, client):
        """Test when no categories are found."""
        mock_db_read.return_value = []

        response = client.get("/services/categories")

        assert response.status_code == 200
        data = response.json()
        assert data == []
        mock_db_read.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_get_categories_database_exception(
        self, mock_logger, mock_db_read, client
    ):
        """Test error handling when database operation fails."""
        mock_db_read.side_effect = Exception("Database connection failed")

        response = client.get("/services/categories")

        assert response.status_code == 200
        data = response.json()
        assert data == []

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        assert "Error getting categories: Database connection failed" in error_msg

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_get_categories_to_dict_exception(
        self, mock_logger, mock_db_read, client
    ):
        """Test error handling when to_dict method fails."""
        # Create a mock category that raises an exception when to_dict is called
        mock_cat = MagicMock()
        mock_cat.to_dict.side_effect = KeyError("name key not found")
        mock_db_read.return_value = [mock_cat]

        response = client.get("/services/categories")

        assert response.status_code == 200
        data = response.json()
        assert data == []

        # Verify error was logged
        mock_logger.error.assert_called_once()


class TestServicesEnumValidation:
    """Test enum validation for category_name parameter."""

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_invalid_category_name_handled(
        self, mock_logger, mock_db_read, client
    ):
        """Test that invalid category names are handled gracefully."""
        # When invalid category is used, getattr fails and exception is caught
        mock_db_read.side_effect = AttributeError(
            "type object 'Categories' has no attribute 'invalid_category'"
        )

        response = client.get("/services/categories?category_name=invalid_category")

        # Should return 200 with empty list due to exception handling
        assert response.status_code == 200
        data = response.json()
        assert data == []

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        assert "Error getting categories:" in error_msg


class TestServicesCatListConstant:
    """Test the cat_list constant used for enum validation."""

    def test_cat_list_contents(self):
        """Test that cat_list contains the expected values."""
        expected_categories = ["is_post", "is_weblink", "is_system"]
        assert cat_list == expected_categories

    def test_cat_list_matches_categories_model(self):
        """Test that cat_list values match Categories model boolean fields."""
        # Verify that the enum values correspond to actual boolean fields in Categories
        for cat_name in cat_list:
            assert hasattr(
                Categories, cat_name
            ), f"Categories model should have {cat_name} field"


class TestServicesIntegration:
    """Integration tests for the services module."""

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    async def test_query_construction_no_filter(self, mock_db_read, client):
        """Test that the SQL query is constructed correctly without filter."""
        mock_db_read.return_value = []

        client.get("/services/categories")

        # Verify the query construction
        mock_db_read.assert_called_once()
        query_arg = mock_db_read.call_args[0][0]
        assert isinstance(query_arg, Select)

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    async def test_query_construction_with_filter(self, mock_db_read, client):
        """Test that the SQL query is constructed correctly with filter."""
        mock_db_read.return_value = []

        client.get("/services/categories?category_name=is_post")

        # Verify the query construction
        mock_db_read.assert_called_once()
        query_arg = mock_db_read.call_args[0][0]
        assert isinstance(query_arg, Select)

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    async def test_response_format(self, mock_db_read, client):
        """Test that the response format is correct."""
        # Create mock categories with proper to_dict response
        mock_cats = []
        for name in ["Tech", "Science", "Art"]:
            mock_cat = MagicMock()
            mock_cat.to_dict.return_value = {
                "name": name,
                "description": f"{name} category",
                "is_post": True,
                "is_weblink": False,
                "is_system": False,
            }
            mock_cats.append(mock_cat)

        mock_db_read.return_value = mock_cats

        response = client.get("/services/categories")

        assert response.status_code == 200
        data = response.json()

        # Should only return the names, not full objects
        assert data == ["Tech", "Science", "Art"]
        assert all(isinstance(item, str) for item in data)


class TestServicesErrorScenarios:
    """Test various error scenarios and edge cases."""

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_getattr_exception(self, mock_logger, mock_db_read, client):
        """Test error handling when getattr fails."""
        mock_db_read.side_effect = AttributeError(
            "Categories has no attribute 'invalid_field'"
        )

        response = client.get("/services/categories?category_name=is_post")

        assert response.status_code == 200
        data = response.json()
        assert data == []

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_list_comprehension_exception(
        self, mock_logger, mock_db_read, client
    ):
        """Test error handling when list comprehension fails."""
        # Create a mock that fails during list comprehension
        mock_cat = MagicMock()
        mock_cat.to_dict.return_value = {}  # Missing 'name' key
        mock_db_read.return_value = [mock_cat]

        response = client.get("/services/categories")

        assert response.status_code == 200
        data = response.json()
        assert data == []

        # Verify error was logged
        mock_logger.error.assert_called_once()


class TestServicesLogging:
    """Test logging functionality in the services module."""

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_error_logging_format(self, mock_logger, mock_db_read, client):
        """Test that errors are logged with proper format."""
        test_exception = Exception("Test database error")
        mock_db_read.side_effect = test_exception

        response = client.get("/services/categories")

        # Verify logging call
        mock_logger.error.assert_called_once()
        log_call = mock_logger.error.call_args[0][0]
        assert "Error getting categories: Test database error" in log_call

    @pytest.mark.asyncio
    @patch("src.endpoints.services.db_ops.read_query")
    @patch("src.endpoints.services.logger")
    async def test_no_logging_on_success(self, mock_logger, mock_db_read, client):
        """Test that no error logging occurs on successful operation."""
        mock_cat = MagicMock()
        mock_cat.to_dict.return_value = {"name": "success-category"}
        mock_db_read.return_value = [mock_cat]

        response = client.get("/services/categories")

        assert response.status_code == 200
        # Verify no error logging occurred
        mock_logger.error.assert_not_called()
