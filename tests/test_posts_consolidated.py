# -*- coding: utf-8 -*-
"""
Consolidated posts tests - combines test_posts.py and test_posts_fixed.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestPosts:
    """Test class for blog post endpoints - consolidated version."""

    def test_posts_index(self, client):
        """Test posts index page."""
        response = client.get("/posts/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.blog_posts.db_ops")
    async def test_get_categories(self, mock_db_ops, client):
        """Test getting post categories."""
        mock_categories = [
            MagicMock(to_dict=lambda: {"name": "technology"}),
            MagicMock(to_dict=lambda: {"name": "science"}),
        ]
        # Use AsyncMock for database operations
        mock_db_ops.read_query = AsyncMock(return_value=mock_categories)

        response = client.get("/posts/categories")
        assert response.status_code == 200
        data = response.json()
        assert "technology" in data
        assert "science" in data

    def test_new_post_form(self, client, bypass_auth):
        """Test new post form loads."""
        response = client.get("/posts/new")
        assert response.status_code == 200
        assert "post" in response.text.lower()

    def test_create_post(self, client, bypass_auth, mock_post):
        """Test creating a new post."""
        # Mock the database operations
        mock_created_post = MagicMock()
        mock_created_post.pkid = "new-post-123"

        with patch("src.endpoints.blog_posts.db_ops") as mock_db_ops:
            mock_db_ops.create_one = AsyncMock(return_value=mock_created_post)
            
            # Mock the redirect view
            mock_post_obj = MagicMock()
            mock_post_obj.to_dict.return_value = mock_post
            mock_db_ops.read_one_record = AsyncMock(return_value=mock_post_obj)

            response = client.post(
                "/posts/new",
                data={
                    "title": "Test Post",
                    "content": "Test content",
                    "category": "technology",
                    "tags": "test,post"
                },
                follow_redirects=False
            )
            
            assert response.status_code in [200, 302, 303]

    @pytest.mark.asyncio
    @patch("src.endpoints.blog_posts.ai")
    @patch("src.endpoints.blog_posts.db_ops")
    async def test_create_post_with_ai(self, mock_db_ops, mock_ai, client, bypass_auth):
        """Test creating a new post with AI features."""
        # Mock AI responses with AsyncMock
        mock_ai.get_tags = AsyncMock(return_value={"tags": ["test"]})
        mock_ai.get_summary = AsyncMock(return_value="Test summary")

        # Mock database response for creation
        mock_post = MagicMock()
        mock_post.pkid = "post-123"
        mock_db_ops.create_one = AsyncMock(return_value=mock_post)

        # Mock database response for the redirect view
        mock_post_obj = MagicMock()
        mock_post_obj.to_dict.return_value = {
            "pkid": "post-123",
            "title": "Test Post",
            "content": "Test content",
            "date_created": "2024-01-01T00:00:00",
            "date_updated": "2024-01-01T00:00:00",
            "user_id": "user-123"
        }
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_post_obj)

        response = client.post(
            "/posts/new",
            data={
                "title": "Test Post",
                "content": "Test content", 
                "category": "technology"
            },
            follow_redirects=False
        )
        
        assert response.status_code in [200, 302, 303]

    def test_read_post(self, client, mock_post):
        """Test reading a post."""
        mock_post_obj = MagicMock()
        mock_post_obj.to_dict.return_value = mock_post

        with (
            patch("src.endpoints.blog_posts.db_ops") as mock_db_ops,
            patch(
                "src.endpoints.blog_posts.date_functions.timezone_update",
                AsyncMock(return_value="Jan 1, 2024"),
            ),
            patch(
                "src.endpoints.blog_posts.get_user_name",
                AsyncMock(return_value="Test User"),
            ),
        ):
            mock_db_ops.read_one_record = AsyncMock(return_value=mock_post_obj)

            response = client.get("/posts/view/post-123")
            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.blog_posts.db_ops")
    @patch("src.endpoints.blog_posts.get_user_name")
    async def test_view_post(self, mock_user_name, mock_db_ops, client, mock_post):
        """Test viewing a post."""
        mock_user_name.return_value = "Test User"
        mock_post_obj = MagicMock()
        mock_post_obj.to_dict.return_value = mock_post
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_post_obj)

        response = client.get("/posts/view/post-123")
        assert response.status_code == 200

    def test_edit_post_form(self, client, bypass_auth, mock_post):
        """Test edit post form."""
        mock_post_obj = MagicMock()
        mock_post_obj.to_dict.return_value = mock_post

        with (
            patch("src.endpoints.blog_posts.db_ops") as mock_db_ops,
            patch(
                "src.endpoints.blog_posts.date_functions.timezone_update",
                AsyncMock(return_value="Jan 1, 2024"),
            ),
        ):
            mock_db_ops.read_one_record = AsyncMock(return_value=mock_post_obj)

            response = client.get("/posts/edit/post-123")
            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.blog_posts.db_ops")
    async def test_edit_post_form_async(self, mock_db_ops, client, bypass_auth, mock_post):
        """Test edit post form (async version)."""
        mock_post_obj = MagicMock()
        mock_post_obj.to_dict.return_value = mock_post
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_post_obj)

        response = client.get("/posts/edit/post-123")
        assert response.status_code == 200

    def test_update_post(self, client, bypass_auth, mock_post):
        """Test updating a post."""
        # Mock old data
        old_post = MagicMock()
        old_post.to_dict.return_value = mock_post

        # Mock updated post
        updated_post = MagicMock()
        updated_post.pkid = "post-123"

        with patch("src.endpoints.blog_posts.db_ops") as mock_db_ops:
            mock_db_ops.read_one_record = AsyncMock(return_value=old_post)
            mock_db_ops.update_one = AsyncMock(return_value=updated_post)

            response = client.post(
                "/posts/edit/post-123",
                data={
                    "title": "Updated Post",
                    "content": "Updated content",
                    "category": "updated"
                },
                follow_redirects=False
            )
            
            assert response.status_code in [200, 302, 303]

    @pytest.mark.asyncio
    @patch("src.endpoints.blog_posts.db_ops")
    async def test_update_post_async(self, mock_db_ops, client, bypass_auth, mock_post):
        """Test updating a post (async version)."""
        mock_post_obj = MagicMock()
        mock_post_obj.to_dict.return_value = mock_post
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_post_obj)
        mock_db_ops.update_one = AsyncMock(return_value=mock_post_obj)

        response = client.post(
            "/posts/edit/post-123",
            data={
                "title": "Updated Post",
                "content": "Updated content"
            },
            follow_redirects=False
        )
        
        assert response.status_code in [200, 302, 303]

    def test_delete_post(self, client, bypass_auth, mock_post):
        """Test deleting a post."""
        mock_post_obj = MagicMock()
        mock_post_obj.to_dict.return_value = mock_post

        with patch("src.endpoints.blog_posts.db_ops") as mock_db_ops:
            mock_db_ops.read_one_record = AsyncMock(return_value=mock_post_obj)
            mock_db_ops.delete_one = AsyncMock(return_value=True)

            response = client.post(
                "/posts/delete/post-123",
                follow_redirects=False
            )
            
            assert response.status_code in [200, 302, 303]

    @pytest.mark.asyncio
    @patch("src.endpoints.blog_posts.db_ops")
    async def test_delete_post_async(self, mock_db_ops, client, bypass_auth, mock_post):
        """Test deleting a post (async version)."""
        mock_post_obj = MagicMock()
        mock_post_obj.to_dict.return_value = mock_post
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_post_obj)
        mock_db_ops.delete_one = AsyncMock(return_value=True)

        response = client.post("/posts/delete/post-123", follow_redirects=False)
        assert response.status_code in [200, 302, 303]

    def test_posts_pagination(self, client):
        """Test posts pagination."""
        mock_posts = [
            MagicMock(
                to_dict=lambda: {
                    "pkid": "1",
                    "title": "Test Post",
                    "date_created": "2024-01-01T00:00:00",
                    "date_updated": "2024-01-01T00:00:00",
                }
            )
        ]
        
        with (
            patch("src.endpoints.blog_posts.db_ops") as mock_db_ops,
            patch(
                "src.endpoints.blog_posts.date_functions.update_timezone_for_dates",
                AsyncMock(return_value=mock_posts)
            )
        ):
            mock_db_ops.read_query = AsyncMock(return_value=mock_posts)
            mock_db_ops.count_query = AsyncMock(return_value=1)

            response = client.get("/posts/?page=1")
            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.blog_posts.db_ops")
    async def test_posts_pagination_async(self, mock_db_ops, client):
        """Test posts pagination (async version)."""
        mock_posts = [
            MagicMock(to_dict=lambda: {
                "pkid": "1", 
                "title": "Test Post",
                "date_created": "2024-01-01T00:00:00"
            })
        ]
        mock_db_ops.read_query = AsyncMock(return_value=mock_posts)
        mock_db_ops.count_query = AsyncMock(return_value=1)

        response = client.get("/posts/?page=1")
        assert response.status_code == 200

    def test_get_posts_list(self, client):
        """Test getting posts list."""
        response = client.get("/posts/")
        assert response.status_code == 200

    def test_posts_list_with_mock_data(self, client):
        """Test posts list with mocked data."""
        mock_posts = [
            MagicMock(to_dict=lambda: {
                "pkid": "1",
                "title": "Test Post", 
                "date_created": "2024-01-01T00:00:00"
            })
        ]
        
        with patch("src.endpoints.blog_posts.db_ops") as mock_db_ops:
            mock_db_ops.read_query = AsyncMock(return_value=mock_posts)
            mock_db_ops.count_query = AsyncMock(return_value=1)

            response = client.get("/posts/")
            assert response.status_code == 200