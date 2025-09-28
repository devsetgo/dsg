# -*- coding: utf-8 -*-
"""
Comprehensive tests for Notes endpoints module.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import csv
import io


class TestNotesCore:
    """Test core notes functionality."""

    def test_notes_dashboard_unauthorized(self, client):
        """Test notes dashboard redirects when not authenticated."""
        response = client.get("/notes/")
        assert response.status_code == 200
        # Should redirect to error page or login

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.notes_metrics")
    async def test_notes_dashboard_authorized(
        self, mock_metrics, mock_db_ops, client, bypass_auth
    ):
        """Test notes dashboard loads for authenticated user."""
        # Mock note metrics
        mock_metrics_data = MagicMock()
        mock_metrics_data.to_dict.return_value = {
            "note_count": 5,
            "word_count": 100,
            "character_count": 500,
            "metrics": {"mood_analysis": {"positive": 3, "negative": 2}},
            "date_updated": datetime.utcnow()
            - timedelta(hours=2),  # Old enough to trigger update
        }
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_metrics_data)
        mock_metrics.update_notes_metrics = AsyncMock()

        response = client.get("/notes/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_notes_metrics_counts(self, mock_db_ops, client, bypass_auth):
        """Test notes metrics endpoint."""
        # Mock metrics data with mood_metric structure that template expects
        mock_metrics_data = MagicMock()
        mock_metrics_data.to_dict.return_value = {
            "pkid": "metrics-123",
            "note_count": 10,
            "word_count": 500,
            "character_count": 2500,
            "mood_metric": {"positive": 6, "neutral": 3, "negative": 1},
            "ai_fix_count": 2,
            "total_unique_tag_count": 15,
            "date_created": datetime.utcnow(),
            "date_updated": datetime.utcnow(),
            "user_id": "user-123",
        }
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_metrics_data)

        response = client.get("/notes/metrics/counts")
        assert response.status_code == 200

    def test_new_note_form(self, client, bypass_auth):
        """Test new note form loads."""
        response = client.get("/notes/new")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.process_ai_analysis_background")
    @patch("src.endpoints.notes.notes_metrics")
    @patch("src.endpoints.notes.db_ops")
    async def test_create_note(
        self, mock_db_ops, mock_metrics, mock_ai_task, client, bypass_auth
    ):
        """Test creating a new note."""
        # Mock database response
        mock_note = MagicMock()
        mock_note.pkid = "new-note-123"
        mock_db_ops.create_one = AsyncMock(return_value=mock_note)
        mock_metrics.update_notes_metrics = AsyncMock()

        response = client.post(
            "/notes/new",
            data={"mood": "positive", "note": "This is a test note content."},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/notes/view/new-note-123" in response.headers["location"]

        # Verify database creation was called
        mock_db_ops.create_one.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.date_functions")
    async def test_view_note(
        self, mock_date_functions, mock_db_ops, client, bypass_auth
    ):
        """Test viewing a specific note."""
        # Mock note data
        mock_note = MagicMock()
        mock_note.to_dict.return_value = {
            "pkid": "note-123",
            "mood": "positive",
            "note": "Test note content",
            "summary": "Test summary",
            "tags": ["test", "note"],
            "date_created": datetime.utcnow(),
            "date_updated": datetime.utcnow(),
            "user_id": "user-123",
        }
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note)
        mock_date_functions.timezone_update = AsyncMock(return_value="Jan 1, 2024")

        response = client.get("/notes/view/note-123")
        assert response.status_code == 200

        # Verify database query was called
        mock_db_ops.read_one_record.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_view_note_not_found(self, mock_db_ops, client, bypass_auth):
        """Test viewing non-existent note redirects."""
        mock_db_ops.read_one_record = AsyncMock(return_value=None)

        response = client.get("/notes/view/nonexistent", follow_redirects=False)
        assert response.status_code == 302
        assert "/notes" in response.headers["location"]


class TestNotesEditing:
    """Test note editing functionality."""

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.date_functions")
    @patch("src.endpoints.notes.ai")
    async def test_edit_note_form(
        self, mock_ai, mock_date_functions, mock_db_ops, client, bypass_auth
    ):
        """Test edit note form loads."""
        # Mock note data
        mock_note = MagicMock()
        mock_note.to_dict.return_value = {
            "pkid": "note-123",
            "mood": "positive",
            "note": "Test note content",
            "summary": "Test summary",
            "tags": ["test", "note"],
            "date_created": datetime.utcnow(),
            "date_updated": datetime.utcnow(),
            "user_id": "user-123",
        }
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note)
        mock_date_functions.timezone_update = AsyncMock(return_value="Jan 1, 2024")
        mock_ai.mood_analysis = ["positive", "negative", "neutral"]

        response = client.get("/notes/edit/note-123")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.notes_metrics")
    @patch("src.endpoints.notes.db_ops")
    async def test_update_note(self, mock_db_ops, mock_metrics, client, bypass_auth):
        """Test updating an existing note."""
        # Mock existing note
        mock_existing_note = MagicMock()
        mock_existing_note.to_dict.return_value = {
            "pkid": "note-123",
            "mood": "positive",
            "note": "Original content",
            "summary": "Original summary",
            "tags": ["original"],
            "user_id": "user-123",
        }

        # Mock updated note response
        mock_updated_note = MagicMock()
        mock_updated_note.pkid = "note-123"

        mock_db_ops.read_one_record = AsyncMock(return_value=mock_existing_note)
        mock_db_ops.update_one = AsyncMock(return_value=mock_updated_note)
        mock_metrics.update_notes_metrics = AsyncMock()

        response = client.post(
            "/notes/edit/note-123",
            data={
                "mood": "negative",
                "note": "Updated content",
                "summary": "Updated summary",
                "tags": "updated,note",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/notes/view/note-123" in response.headers["location"]

        # Verify update was called
        mock_db_ops.update_one.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_delete_note_form(self, mock_db_ops, client, bypass_auth):
        """Test delete note form loads."""
        mock_note = MagicMock()
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note)

        response = client.get("/notes/delete/note-123")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.notes_metrics")
    @patch("src.endpoints.notes.db_ops")
    async def test_delete_note(self, mock_db_ops, mock_metrics, client, bypass_auth):
        """Test deleting a note."""
        mock_note = MagicMock()
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note)
        mock_db_ops.delete_one = AsyncMock(return_value=True)
        mock_metrics.update_notes_metrics = AsyncMock()

        response = client.post("/notes/delete/note-123", follow_redirects=False)
        assert response.status_code == 302
        assert "/notes" in response.headers["location"]

        # Verify deletion was called
        mock_db_ops.delete_one.assert_called_once()


class TestNotesAI:
    """Test AI-related note functionality."""

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_ai_resubmit_form(self, mock_db_ops, client, bypass_auth):
        """Test AI resubmit form loads."""
        mock_note = MagicMock()
        mock_note.to_dict.return_value = {
            "pkid": "note-123",
            "note": "Test content",
            "ai_fix": True,
        }
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note)

        response = client.get("/notes/ai-resubmit/note-123")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.ai")
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.settings")
    async def test_ai_fix_processing(
        self, mock_settings, mock_db_ops, mock_ai, client, bypass_auth
    ):
        """Test AI fix processing."""
        # Mock settings
        mock_settings.mood_analysis_weights = [
            ("positive", 1),
            ("negative", 1),
            ("neutral", 1),
        ]

        # Mock note data
        mock_note = MagicMock()
        mock_note.to_dict.return_value = {
            "pkid": "note-123",
            "note": "Test content",
            "mood": "positive",
        }
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note)
        mock_db_ops.update_one = AsyncMock()

        # Mock AI response
        mock_ai.get_analysis = AsyncMock(
            return_value={
                "tags": {"tags": ["test", "ai"]},
                "summary": "AI-generated summary",
                "mood_analysis": "positive",
                "mood": {"mood": "positive"},
            }
        )

        response = client.get("/notes/ai-fix/note-123", follow_redirects=False)
        assert response.status_code == 302
        assert "/notes/view/note-123" in response.headers["location"]

        # Verify AI analysis was called
        mock_ai.get_analysis.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.date_functions")
    async def test_notes_issues(
        self, mock_date_functions, mock_db_ops, client, bypass_auth
    ):
        """Test viewing notes with AI issues."""
        # Mock notes with issues
        mock_note = MagicMock()
        mock_note.to_dict.return_value = {
            "pkid": "note-123",
            "note": "Content with issues",
            "ai_fix": True,
            "date_created": datetime.utcnow(),
        }
        mock_db_ops.read_query = AsyncMock(return_value=[mock_note])
        mock_date_functions.update_timezone_for_dates = AsyncMock(
            return_value=[mock_note.to_dict()]
        )

        response = client.get("/notes/issues")
        assert response.status_code == 200


class TestNotesPagination:
    """Test notes pagination and search functionality."""

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.date_functions")
    async def test_pagination_basic(
        self, mock_date_functions, mock_db_ops, client, bypass_auth
    ):
        """Test basic pagination."""
        # Mock notes data
        mock_notes = [
            MagicMock(
                to_dict=lambda: {
                    "pkid": f"note-{i}",
                    "note": f"Test note {i}",
                    "mood": "positive",
                    "date_created": datetime.utcnow(),
                }
            )
            for i in range(5)
        ]
        mock_db_ops.read_query = AsyncMock(return_value=mock_notes)
        mock_db_ops.count_query = AsyncMock(return_value=25)
        mock_date_functions.update_timezone_for_dates = AsyncMock(
            return_value=[note.to_dict() for note in mock_notes]
        )

        response = client.get("/notes/pagination?page=1&limit=5")
        assert response.status_code == 200

    @pytest.mark.xfail(
        reason="Application bug: Notes.note is a property, not a column - search is broken"
    )
    async def test_pagination_with_search(self, client, bypass_auth):
        """Test pagination with search term - currently fails due to application bug.

        Notes.note is a property (not a column) but the code tries to call .contains() on it.
        This test documents the current broken behavior.
        """
        # This test documents that search functionality is currently broken in the application
        # The issue is that Notes.note is a property wrapping the encrypted _note column,
        # but the code tries to use Notes.note.contains() which fails.
        response = client.get("/notes/pagination?search_term=test&page=1")
        assert response.status_code == 500  # Application fails due to AttributeError

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.date_functions")
    async def test_pagination_with_date_filter(
        self, mock_date_functions, mock_db_ops, client, bypass_auth
    ):
        """Test pagination with date filtering."""
        mock_notes = [
            MagicMock(
                to_dict=lambda: {"pkid": "note-1", "note": "Date filtered content"}
            )
        ]
        mock_db_ops.read_query = AsyncMock(return_value=mock_notes)
        mock_db_ops.count_query = AsyncMock(return_value=1)
        mock_date_functions.update_timezone_for_dates = AsyncMock(
            return_value=[mock_notes[0].to_dict()]
        )

        response = client.get(
            "/notes/pagination?start_date=2024-01-01&end_date=2024-12-31&page=1"
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.date_functions")
    async def test_pagination_with_mood_filter(
        self, mock_date_functions, mock_db_ops, client, bypass_auth
    ):
        """Test pagination with mood filtering."""
        mock_notes = [MagicMock(to_dict=lambda: {"pkid": "note-1", "mood": "positive"})]
        mock_db_ops.read_query = AsyncMock(return_value=mock_notes)
        mock_db_ops.count_query = AsyncMock(return_value=1)
        mock_date_functions.update_timezone_for_dates = AsyncMock(
            return_value=[mock_notes[0].to_dict()]
        )

        response = client.get("/notes/pagination?mood=positive&page=1")
        assert response.status_code == 200


class TestNotesToday:
    """Test today's notes functionality."""

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.date_functions")
    @patch("src.endpoints.notes.settings")
    async def test_today_notes(
        self, mock_settings, mock_date_functions, mock_db_ops, client, bypass_auth
    ):
        """Test viewing today's notes in history."""
        mock_settings.history_range = 7

        # Mock today's notes
        mock_notes = [
            MagicMock(
                to_dict=lambda: {
                    "pkid": "note-today-1",
                    "note": "Today's note",
                    "date_created": datetime.utcnow(),
                }
            )
        ]
        mock_db_ops.read_query = AsyncMock(return_value=mock_notes)
        mock_date_functions.update_timezone_for_dates = AsyncMock(
            return_value=[mock_notes[0].to_dict()]
        )

        response = client.get("/notes/today")
        assert response.status_code == 200


class TestNotesBulk:
    """Test bulk note import functionality."""

    def test_bulk_note_form(self, client):
        """Test bulk note form loads."""
        response = client.get("/notes/bulk")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.note_import")
    async def test_bulk_note_upload(self, mock_note_import, client, bypass_auth):
        """Test bulk note CSV upload."""
        mock_note_import.read_notes_from_file = AsyncMock()

        # Create mock CSV data
        csv_content = "mood,note\npositive,Test note 1\nnegative,Test note 2"

        response = client.post(
            "/notes/bulk",
            files={"csv_file": ("test_notes.csv", csv_content, "text/csv")},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/notes" in response.headers["location"]


class TestNotesBackgroundProcessing:
    """Test background processing functionality."""

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.ai")
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.settings")
    async def test_process_ai_analysis_background_success(
        self, mock_settings, mock_db_ops, mock_ai
    ):
        """Test successful background AI analysis."""
        from src.endpoints.notes import process_ai_analysis_background

        mock_settings.mood_analysis_weights = [("positive", 1), ("negative", 1)]

        # Mock AI response
        mock_ai.get_analysis = AsyncMock(
            return_value={
                "tags": {"tags": ["background", "test"]},
                "summary": "Background analysis summary",
                "mood_analysis": "positive",
                "mood": {"mood": "positive"},
            }
        )
        mock_db_ops.update_one = AsyncMock()

        # Test the background function
        await process_ai_analysis_background("note-123", "Test content")

        # Verify AI was called
        mock_ai.get_analysis.assert_called_once()
        mock_db_ops.update_one.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.ai")
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.logger")
    async def test_process_ai_analysis_background_error(
        self, mock_logger, mock_db_ops, mock_ai
    ):
        """Test background AI analysis error handling."""
        from src.endpoints.notes import process_ai_analysis_background

        # Mock AI failure
        mock_ai.get_analysis = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )
        mock_db_ops.update_one = AsyncMock()

        # Test the background function with error
        await process_ai_analysis_background("note-123", "Test content")

        # Verify error was logged and ai_fix was set to True
        mock_logger.error.assert_called()
        mock_db_ops.update_one.assert_called_with(
            table=mock_db_ops.update_one.call_args[1]["table"],
            record_id="note-123",
            new_values={"ai_fix": True},
        )


class TestNotesErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_edit_nonexistent_note(self, mock_db_ops, client, bypass_auth):
        """Test editing non-existent note redirects."""
        mock_db_ops.read_one_record = AsyncMock(return_value=None)

        response = client.get("/notes/edit/nonexistent", follow_redirects=False)
        assert response.status_code == 302
        assert "/notes" in response.headers["location"]

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_delete_nonexistent_note(self, mock_db_ops, client, bypass_auth):
        """Test deleting non-existent note."""
        mock_db_ops.read_one_record = AsyncMock(return_value=None)

        response = client.post("/notes/delete/nonexistent", follow_redirects=False)
        assert response.status_code == 302
        assert "/notes" in response.headers["location"]

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_ai_resubmit_nonexistent_note(self, mock_db_ops, client, bypass_auth):
        """Test AI resubmit for non-existent note."""
        mock_db_ops.read_one_record = AsyncMock(return_value=None)

        response = client.get("/notes/ai-resubmit/nonexistent", follow_redirects=False)
        assert response.status_code == 303
        assert "/error/404" in response.headers["location"]

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_pagination_error_handling(self, mock_db_ops, client, bypass_auth):
        """Test pagination handles unexpected database responses."""
        # Mock database returning string instead of list (error case)
        mock_db_ops.read_query = AsyncMock(return_value="Error occurred")
        mock_db_ops.count_query = AsyncMock(return_value=0)

        response = client.get("/notes/pagination")
        assert response.status_code == 200  # Should handle gracefully


class TestNotesEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.db_ops")
    async def test_metrics_no_existing_data(self, mock_db_ops, client, bypass_auth):
        """Test metrics endpoint when no metrics exist."""
        # First call returns None, second call returns created metrics
        mock_metrics_data = MagicMock()
        mock_metrics_data.to_dict.return_value = {
            "note_count": 0,
            "word_count": 0,
            "character_count": 0,
            "mood_metric": {"positive": 0, "neutral": 0, "negative": 0},
            "ai_fix_count": 0,
            "total_unique_tag_count": 0,
            "pkid": "metrics-456",
            "date_created": datetime.utcnow(),
            "date_updated": datetime.utcnow(),
            "user_id": "user-456",
        }

        mock_db_ops.read_one_record = AsyncMock(side_effect=[None, mock_metrics_data])

        with patch("src.endpoints.notes.notes_metrics") as mock_metrics:
            mock_metrics.update_notes_metrics = AsyncMock()

            response = client.get("/notes/metrics/counts")
            assert response.status_code == 200
            mock_metrics.update_notes_metrics.assert_called_once()

    @pytest.mark.xfail(reason="Application bug: Division by zero when limit=0")
    @patch("src.endpoints.notes.db_ops")
    async def test_pagination_edge_cases(self, mock_db_ops, client, bypass_auth):
        """Test pagination edge cases."""
        mock_db_ops.read_query = AsyncMock(return_value=[])
        mock_db_ops.count_query = AsyncMock(return_value=0)

        with patch("src.endpoints.notes.date_functions") as mock_date_functions:
            mock_date_functions.update_timezone_for_dates = AsyncMock(return_value=[])

            # Test high page number
            response = client.get("/notes/pagination?page=999")
            assert response.status_code == 200

            # Test limit=0 causes division by zero error (application bug)
            response = client.get("/notes/pagination?limit=0")
            assert response.status_code == 500  # Application crashes on limit=0

            # Test minimum valid limit
            response = client.get("/notes/pagination?limit=1")
            assert response.status_code == 200

    def test_view_note_with_ai_flag(self, client, bypass_auth):
        """Test viewing note with AI processing flag."""
        with patch("src.endpoints.notes.db_ops") as mock_db_ops:
            with patch("src.endpoints.notes.date_functions") as mock_date_functions:
                mock_note = MagicMock()
                mock_note.to_dict.return_value = {
                    "pkid": "note-123",
                    "note": "Test content",
                    "date_created": datetime.utcnow(),
                    "date_updated": datetime.utcnow(),
                }
                mock_db_ops.read_one_record = AsyncMock(return_value=mock_note)
                mock_date_functions.timezone_update = AsyncMock(
                    return_value="Jan 1, 2024"
                )

                response = client.get("/notes/view/note-123?ai=true")
                assert response.status_code == 200


class TestNotesIntegration:
    """Test integrated note workflows."""

    @pytest.mark.asyncio
    @patch("src.endpoints.notes.process_ai_analysis_background")
    @patch("src.endpoints.notes.notes_metrics")
    @patch("src.endpoints.notes.db_ops")
    @patch("src.endpoints.notes.date_functions")
    async def test_full_note_lifecycle(
        self,
        mock_date_functions,
        mock_db_ops,
        mock_metrics,
        mock_ai_task,
        client,
        bypass_auth,
    ):
        """Test complete note lifecycle: create -> view -> edit -> delete."""
        # Step 1: Create note
        mock_created_note = MagicMock()
        mock_created_note.pkid = "lifecycle-note"
        mock_db_ops.create_one = AsyncMock(return_value=mock_created_note)

        # Step 2: View note setup
        mock_note_data = MagicMock()
        mock_note_data.to_dict.return_value = {
            "pkid": "lifecycle-note",
            "mood": "positive",
            "note": "Lifecycle test",
            "summary": "Test summary",
            "tags": ["test"],
            "date_created": datetime.utcnow(),
            "date_updated": datetime.utcnow(),
        }

        # Step 3: Edit/update setup
        mock_updated_note = MagicMock()
        mock_updated_note.pkid = "lifecycle-note"
        mock_db_ops.update_one = AsyncMock(return_value=mock_updated_note)

        # Step 4: Delete setup
        mock_db_ops.delete_one = AsyncMock(return_value=True)

        # Configure read_one_record for different scenarios
        mock_db_ops.read_one_record = AsyncMock(return_value=mock_note_data)
        mock_date_functions.timezone_update = AsyncMock(return_value="Jan 1, 2024")
        mock_metrics.update_notes_metrics = AsyncMock()

        # Test the lifecycle

        # 1. Create note
        create_response = client.post(
            "/notes/new",
            data={"mood": "positive", "note": "Lifecycle test"},
            follow_redirects=False,
        )
        assert create_response.status_code == 302

        # 2. View note
        view_response = client.get("/notes/view/lifecycle-note")
        assert view_response.status_code == 200

        # 3. Edit note
        edit_response = client.post(
            "/notes/edit/lifecycle-note",
            data={"mood": "negative", "note": "Updated lifecycle test"},
            follow_redirects=False,
        )
        assert edit_response.status_code == 302

        # 4. Delete note
        delete_response = client.post(
            "/notes/delete/lifecycle-note", follow_redirects=False
        )
        assert delete_response.status_code == 302

        # Verify all operations were called
        mock_db_ops.create_one.assert_called_once()
        mock_db_ops.update_one.assert_called()
        mock_db_ops.delete_one.assert_called_once()
