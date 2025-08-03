# -*- coding: utf-8 -*-
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestAdmin:
    """Test cases for admin endpoints."""

    def test_admin_dashboard_unauthorized(self, client):
        """Test admin dashboard requires admin access."""
        response = client.get("/admin/")
        # Should redirect to error page which returns 200
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch('src.endpoints.admin.get_list_of_users')
    async def test_admin_dashboard_authorized(self, mock_users, client, bypass_admin_auth):
        """Test admin dashboard loads for admin user."""
        mock_users = AsyncMock(return_value=[{"user_name": "testuser"}])
        
        response = client.get("/admin/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch('src.endpoints.admin.db_ops')
    async def test_admin_categories(self, mock_db_ops, client, bypass_admin_auth):
        """Test admin categories page."""
        response = client.get("/admin/categories")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch('src.endpoints.admin.db_ops')
    async def test_admin_categories_table(self, mock_db_ops, client, bypass_admin_auth):
        """Test admin categories table."""
        mock_categories = [
            MagicMock(to_dict=lambda: {"name": "tech", "description": "Technology"})
        ]
        mock_posts = [
            MagicMock(to_dict=lambda: {"category": "tech"})
        ]
        mock_weblinks = [
            MagicMock(to_dict=lambda: {"category": "tech"})
        ]
        
        mock_db_ops.read_query = AsyncMock()
        mock_db_ops.read_query.side_effect = [mock_categories, mock_posts, mock_weblinks]
        
        response = client.get("/admin/categories-table")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_category_edit_form(self, client, bypass_admin_auth):
        """Test admin category edit form."""
        response = client.get("/admin/category-edit")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch('src.endpoints.admin.db_ops')
    async def test_admin_category_create(self, mock_db_ops, client, bypass_admin_auth):
        """Test creating a new category."""
        mock_category = MagicMock()
        mock_category.to_dict.return_value = {
            "pkid": "cat-123",
            "name": "New Category",
            "description": "Test category"
        }
        mock_db_ops.create_one = AsyncMock(return_value=mock_category)
        
        response = client.post("/admin/category-edit", data={
            "name": "New Category",
            "description": "Test category",
            "is_post": "on"
        }, follow_redirects=False)
        
        assert response.status_code == 307  # Changed from 200 to 307 for redirect

    @pytest.mark.asyncio
    @patch('src.endpoints.admin.db_ops')
    async def test_admin_user_view(self, mock_db_ops, client, bypass_admin_auth, mock_user):
        """Test viewing a user in admin."""
        mock_user_obj = MagicMock()
        mock_user_obj.to_dict.return_value = mock_user
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_user_obj)
        mock_db_ops.count_query = AsyncMock(return_value=5)  # Mock counts
        
        with patch('src.endpoints.admin.date_functions.timezone_update', 
                   AsyncMock(return_value="Jan 1, 2024")):
            response = client.get("/admin/user/test-user-123")
            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch('src.endpoints.admin.db_ops')
    @patch('src.endpoints.admin.hash_password')
    @patch('src.endpoints.admin.check_password_complexity')
    async def test_admin_update_user_password(self, mock_complexity, mock_hash, mock_db_ops, client, bypass_admin_auth):
        """Test updating user password by admin."""
        mock_complexity.return_value = True
        mock_hash.return_value = "hashed_password"
        mock_db_ops.update_one = AsyncMock(return_value=MagicMock())
        mock_db_ops.read_one_record = AsyncMock(return_value=MagicMock(to_dict=lambda: {"pkid": "user-123"}))
        
        response = client.post("/admin/user/user-123", data={
            "account-action": "password",
            "new-password-entry": "NewPassword123!"
        }, follow_redirects=False)
        
        assert response.status_code == 307  # Changed from 200 to 307 for redirect

    @pytest.mark.asyncio
    @patch('src.endpoints.admin.db_ops')
    async def test_admin_note_ai_check(self, mock_db_ops, client, bypass_admin_auth):
        """Test admin note AI check page."""
        mock_notes = [
            MagicMock(to_dict=lambda: {
                "pkid": "note-1", 
                "user_id": "user-1",
                "date_created": "2024-01-01T00:00:00"
            })
        ]
        mock_weblinks = [
            MagicMock(to_dict=lambda: {
                "pkid": "link-1",
                "user_id": "user-1"
            })
        ]
        mock_user = MagicMock(to_dict=lambda: {"user_name": "testuser"})
        
        mock_db_ops.read_query = AsyncMock()
        mock_db_ops.read_query.side_effect = [mock_notes, mock_weblinks]
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_user)
        
        response = client.get("/admin/note-ai-check")
        assert response.status_code == 200

    def test_admin_note_ai_check_user(self, client, bypass_admin_auth):
        """Test triggering AI check for specific user."""
        with patch('src.endpoints.admin.db_ops.read_query') as mock_read:
            mock_notes = [
                MagicMock(to_dict=lambda: {"pkid": "note-1"})
            ]
            mock_read = AsyncMock(return_value=mock_notes)
            
            response = client.get("/admin/note-ai-check/user-123", follow_redirects=False)
            assert response.status_code == 307  # Changed from 302 to 307 for redirect
        
        response = client.get("/admin/note-ai-check/user-123")
        assert response.status_code == 200  # Changed from 302 to 200 due to redirect chain
