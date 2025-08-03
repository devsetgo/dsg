# -*- coding: utf-8 -*-
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestPages:
    """Test cases for pages endpoints."""

    def test_root_redirect(self, client):
        """Test root endpoint redirects to index."""
        response = client.get("/pages/", follow_redirects=False)
        assert response.status_code == 307  # Changed from 302 to 307 for redirect

    def test_app_info(self, client):
        """Test app info endpoint."""
        response = client.get("/pages/app-info")
        assert response.status_code == 200
        assert "version" in response.text.lower()

    @pytest.mark.asyncio
    @patch("src.endpoints.pages.db_ops")
    async def test_index_page(self, mock_db_ops, client):
        """Test index page loads with data."""
        # Mock database responses
        mock_weblinks = [
            MagicMock(
                to_dict=lambda: {
                    "pkid": "1",
                    "title": "Test Link",
                    "date_created": "2024-01-01T00:00:00",
                }
            )
        ]
        mock_posts = [
            MagicMock(
                to_dict=lambda: {
                    "pkid": "1",
                    "title": "Test Post",
                    "date_created": "2024-01-01T00:00:00",
                }
            )
        ]

        mock_db_ops.read_query = AsyncMock()
        mock_db_ops.read_query.side_effect = [mock_weblinks, mock_posts]

        with patch(
            "src.endpoints.pages.update_timezone_for_dates",
            AsyncMock(side_effect=lambda data, user_timezone: data),
        ):
            response = client.get("/pages/index")
            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.functions.github.call_github_repos")
    @patch("src.functions.github.call_github_user")
    async def test_about_page(self, mock_user, mock_repos, client):
        """Test about page with GitHub data."""
        mock_repos = AsyncMock(
            return_value=[{"name": "test-repo", "description": "Test"}]
        )
        mock_user = AsyncMock(return_value={"login": "testuser", "name": "Test User"})

        response = client.get("/pages/about")
        assert response.status_code == 200

    def test_public_debt(self, client):
        """Test public debt endpoint."""
        with patch("src.endpoints.pages.get_public_debt") as mock_debt:
            mock_debt.return_value = [
                {
                    "record_date": "2024-01-01",
                    "tot_pub_debt_out_amt": "1000000",
                    "debt_held_public_amt": "800000",
                    "intragov_hold_amt": "200000",
                }
            ]

            response = client.get("/pages/public-debt")
            assert response.status_code == 200

    def test_data_page(self, client):
        """Test data page endpoint."""
        response = client.get("/pages/data")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_about_standalone(self, client):
        """Test about page standalone."""
        with patch("src.functions.github.call_github_repos") as mock_repos:
            with patch("src.functions.github.call_github_user") as mock_user:
                mock_repos = AsyncMock(return_value=[])
                mock_user = AsyncMock(return_value={"login": "test"})
                response = client.get("/pages/about")
                assert response.status_code == 200

    def test_data_standalone(self, client):
        """Test data page standalone."""
        response = client.get("/pages/data")
        assert response.status_code == 200
