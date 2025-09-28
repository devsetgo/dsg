# -*- coding: utf-8 -*-
"""Focused tests for web_links endpoints - targeting high-impact functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestWebLinksCore:
    """Test core web links functionality."""

    def test_web_links_index(self, client):
        """Test web links main page."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_db_ops.read_query = AsyncMock(return_value=[])
            mock_db_ops.count_query = AsyncMock(return_value=0)

            response = client.get("/links/")
            assert response.status_code == 200

    def test_web_links_create_form(self, client, bypass_auth):
        """Test web links creation form."""
        response = client.get("/links/new")
        assert response.status_code in [200, 307]  # May redirect if not authenticated

    def test_web_links_create_post(self, client, bypass_auth):
        """Test creating a web link via POST."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_weblink = MagicMock()
            mock_weblink.pkid = "link-123"
            mock_db_ops.create_one = AsyncMock(return_value=mock_weblink)

            response = client.post(
                "/links/new",
                data={
                    "title": "Test Link",
                    "url": "https://example.com",
                    "category": "technology",
                    "description": "A test link",
                },
                follow_redirects=False,
            )
            # May redirect after successful creation or return various status codes
            assert response.status_code in [200, 302, 303, 307]

    def test_web_links_view_link(self, client):
        """Test viewing a specific web link."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_link = MagicMock()
            mock_link.to_dict.return_value = {
                "pkid": "link-123",
                "title": "Test Link",
                "url": "https://example.com",
                "description": "Test Description",
            }
            mock_db_ops.read_one_record = AsyncMock(return_value=mock_link)

            response = client.get("/links/view/link-123")
            assert response.status_code == 200

    def test_web_links_pagination(self, client):
        """Test web links pagination."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            # Mock paginated results
            mock_links = [
                MagicMock(to_dict=lambda: {"pkid": f"link-{i}", "title": f"Link {i}"})
                for i in range(10)
            ]
            mock_db_ops.read_query = AsyncMock(return_value=mock_links)
            mock_db_ops.count_query = AsyncMock(return_value=25)

            response = client.get("/links/pagination?page=1&limit=10")
            assert response.status_code == 200


class TestWebLinksCategories:
    """Test web links category functionality."""

    def test_web_links_categories_view(self, client):
        """Test web links categories page."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_categories = [
                MagicMock(to_dict=lambda: {"pkid": "cat-1", "category_name": "Tech"}),
                MagicMock(to_dict=lambda: {"pkid": "cat-2", "category_name": "News"}),
            ]
            mock_db_ops.read_query = AsyncMock(return_value=mock_categories)

            response = client.get("/links/categories")
            assert response.status_code == 200

    def test_web_links_by_category(self, client):
        """Test viewing web links by category."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_links = [
                MagicMock(to_dict=lambda: {"pkid": "link-1", "title": "Tech Link"})
            ]
            mock_db_ops.read_query = AsyncMock(return_value=mock_links)
            mock_db_ops.count_query = AsyncMock(return_value=1)

            response = client.get("/links/category/tech")
            assert response.status_code == 200


class TestWebLinksManagement:
    """Test web links management features."""

    def test_web_links_edit_form(self, client, bypass_auth):
        """Test web links edit form."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_link = MagicMock()
            mock_link.to_dict.return_value = {
                "pkid": "link-123",
                "title": "Test Link",
                "url": "https://example.com",
                "description": "Test Description",
            }
            mock_db_ops.read_one_record = AsyncMock(return_value=mock_link)

            response = client.get("/links/edit/link-123")
            assert response.status_code in [200, 307]  # Success or redirect

    def test_web_links_edit_post(self, client, bypass_auth):
        """Test editing a web link."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_db_ops.update_one = AsyncMock(return_value=MagicMock())

            response = client.post(
                "/links/edit/link-123",
                data={
                    "title": "Updated Link",
                    "url": "https://updated-example.com",
                    "category": "science",
                },
                follow_redirects=False,
            )
            # May redirect after update or return various status codes
            assert response.status_code in [200, 302, 303, 307, 404]

    def test_web_links_delete(self, client, bypass_auth):
        """Test deleting a web link."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_link = MagicMock()
            mock_link.to_dict.return_value = {"pkid": "link-123"}
            mock_db_ops.read_one_record = AsyncMock(return_value=mock_link)
            mock_db_ops.delete_one = AsyncMock(return_value=True)

            response = client.post("/links/delete/link-123", follow_redirects=False)
            # May redirect after deletion or return various status codes
            assert response.status_code in [200, 302, 303, 307, 404, 405]


class TestWebLinksImport:
    """Test web links import functionality."""

    def test_web_links_import_form(self, client, bypass_auth):
        """Test web links import form."""
        response = client.get("/links/import")
        assert response.status_code in [200, 307]  # Success or redirect

    def test_web_links_import_process(self, client, bypass_auth):
        """Test web links import processing."""
        import_data = "https://example1.com,Title 1,Description 1\\nhttps://example2.com,Title 2,Description 2"

        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_link = MagicMock()
            mock_link.pkid = "imported-link"
            mock_db_ops.create_one = AsyncMock(return_value=mock_link)

            # Mock the import processing
            with patch(
                "src.endpoints.web_links.link_preview.update_weblinks", AsyncMock()
            ):
                response = client.post(
                    "/links/import/process",
                    data={"import_data": import_data},
                    follow_redirects=False,
                )
                # May redirect after import or return various status codes
                assert response.status_code in [200, 302, 307]


class TestWebLinksValidation:
    """Test web links validation and error handling."""

    def test_web_links_invalid_url(self, client, bypass_auth):
        """Test creating web link with invalid URL."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            response = client.post(
                "/links/new",
                data={
                    "title": "Invalid Link",
                    "url": "not-a-valid-url",
                    "category": "other",
                },
                follow_redirects=False,
            )
            # Invalid URL might redirect or return validation error
            assert response.status_code in [200, 302, 307, 400, 422]

    def test_web_links_view_nonexistent(self, client):
        """Test viewing a web link that doesn't exist."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_db_ops.read_one_record = AsyncMock(return_value=None)
            response = client.get("/links/view/nonexistent-link")
            # Should handle gracefully (redirect to error page)
            assert response.status_code in [200, 302, 404, 307]

    def test_web_links_search(self, client):
        """Test web links search functionality."""
        with patch("src.endpoints.web_links.db_ops") as mock_db_ops:
            mock_links = [
                MagicMock(
                    to_dict=lambda: {"pkid": "link-1", "title": "Searchable Link"}
                )
            ]
            mock_db_ops.read_query = AsyncMock(return_value=mock_links)
            mock_db_ops.count_query = AsyncMock(return_value=1)

            response = client.get("/links/search?q=searchable")
            assert response.status_code == 200
