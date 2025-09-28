# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestNotes:
    """Test cases for notes endpoints."""

    def test_notes_dashboard_unauthorized(self, client):
        """Test notes dashboard redirects when not authenticated."""
        response = client.get("/notes/")
        # The app redirects to /error/401 which returns 200, so we follow the redirect
        assert response.status_code == 200
        # We could also check that it redirected to the error page
        assert "error" in response.url.path or response.history

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.notes_metrics")
    async def test_notes_dashboard_authorized(
        self, mock_metrics, mock_db_ops, client, bypass_auth, mock_user
    ):
        """Test notes dashboard loads for authenticated user."""
        # Mock note metrics
        mock_metrics_data = MagicMock()
        mock_metrics_data.to_dict.return_value = {
            "note_count": 5,
            "word_count": 100,
            "character_count": 500,
            "metrics": {},
            "date_updated": "2024-01-01T00:00:00",
        }
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_metrics_data)

        response = client.get("/notes/")
        assert response.status_code == 200

    def test_new_note_form(self, client, bypass_auth):
        """Test new note form loads."""
        response = client.get("/notes/new")
        assert response.status_code == 200
        assert "note" in response.text.lower()

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.ai")
    @patch("src.endpoints.notes.db_ops")
    @patch("src.functions.notes_metrics.update_notes_metrics")  # Mock background task
    async def test_create_note(
        self, mock_update_metrics, mock_db_ops, mock_ai, client, bypass_auth
    ):
        """Test creating a new note."""
        # Mock AI response with AsyncMock - include all required keys
        mock_ai.get_analysis = AsyncMock(
            return_value={
                "tags": {"tags": ["test"]},
                "summary": "Test summary",
                "mood_analysis": "happy",
                "mood": {"mood": "positive"},  # Add missing mood key
            }
        )

        # Mock database response
        mock_note = MagicMock()
        mock_note.pkid = "note-123"
        mock_db_ops.create_one = AsyncMock(return_value=mock_note)
        mock_db_ops.update_one = AsyncMock(return_value=MagicMock())  # Fix AsyncMock

        # Mock background task
        mock_update_metrics.return_value = AsyncMock()

        response = client.post(
            "/notes/new",
            data={"mood": "positive", "note": "This is a test note"},
            follow_redirects=False,
        )

        assert response.status_code == 302

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_view_note(self, mock_db_ops, client, bypass_auth, mock_note):
        """Test viewing a specific note."""
        mock_note_obj = MagicMock()
        mock_note_obj.to_dict.return_value = mock_note
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note_obj)

        with patch(
            "src.endpoints.notes.date_functions.timezone_update",
            AsyncMock(return_value="Jan 1, 2024"),
        ):
            response = client.get("/notes/view/note-123")
            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_edit_note_form(self, mock_db_ops, client, bypass_auth, mock_note):
        """Test edit note form loads."""
        mock_note_obj = MagicMock()
        mock_note_obj.to_dict.return_value = mock_note
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note_obj)

        with patch(
            "src.endpoints.notes.date_functions.timezone_update",
            AsyncMock(return_value="Jan 1, 2024"),
        ):
            response = client.get("/notes/edit/note-123")
            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.functions.notes_metrics.update_notes_metrics")  # Mock background task
    async def test_update_note(
        self, mock_update_metrics, mock_db_ops, client, bypass_auth, mock_note
    ):
        """Test updating a note."""
        # Mock old data
        old_note = MagicMock()
        old_note.to_dict.return_value = mock_note

        # Mock updated note
        updated_note = MagicMock()
        updated_note.pkid = "note-123"

        mock_db_ops.read_one_record = AsyncMock(return_value=old_note)
        mock_db_ops.update_one = AsyncMock(return_value=updated_note)

        # Mock background task
        mock_update_metrics.return_value = AsyncMock()

        response = client.post(
            "/notes/edit/note-123",
            data={"note": "Updated note content", "mood": "positive"},
            follow_redirects=False,
        )

        assert response.status_code == 302

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.functions.notes_metrics.update_notes_metrics")  # Mock background task
    async def test_delete_note(
        self, mock_update_metrics, mock_db_ops, client, bypass_auth, mock_note
    ):
        """Test deleting a note."""
        mock_note_obj = MagicMock()
        mock_note_obj.to_dict.return_value = mock_note
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note_obj)
        mock_db_ops.delete_one = AsyncMock(return_value=True)

        # Mock background task
        mock_update_metrics.return_value = AsyncMock()

        response = client.post("/notes/delete/note-123", follow_redirects=False)
        assert response.status_code == 302

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_pagination(self, mock_db_ops, client, bypass_auth):
        """Test notes pagination."""
        mock_notes = [
            MagicMock(
                to_dict=lambda: {
                    "pkid": "1",
                    "note": "Test note",
                    "date_created": "2024-01-01T00:00:00",
                }
            )
        ]
        mock_db_ops.read_query = AsyncMock(return_value=mock_notes)
        mock_db_ops.count_query = AsyncMock(return_value=1)

        with patch(
            "src.endpoints.notes.date_functions.update_timezone_for_dates",
            AsyncMock(return_value=mock_notes),
        ):
            response = client.get("/notes/pagination?page=1&limit=10")
            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.ai")
    @patch("src.endpoints.notes.db_ops")
    async def test_ai_fix_note(
        self, mock_db_ops, mock_ai, client, bypass_auth, mock_note
    ):
        """Test AI fix for a note."""
        mock_note_obj = MagicMock()
        mock_note_obj.to_dict.return_value = mock_note
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note_obj)
        mock_db_ops.update_one = AsyncMock(return_value=mock_note_obj)

        mock_ai.get_analysis = AsyncMock(
            return_value={
                "tags": {"tags": ["fixed"]},
                "summary": "Fixed summary",
                "mood_analysis": "content",
                "mood": {"mood": "positive"},
            }
        )

        response = client.get("/notes/ai-fix/note-123", follow_redirects=False)
        assert response.status_code == 302
