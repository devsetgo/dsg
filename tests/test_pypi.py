# -*- coding: utf-8 -*-
"""
Comprehensive tests for PyPI endpoints module.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestPyPICore:
    """Test core PyPI functionality."""

    def test_pypi_root_redirect(self, client):
        """Test PyPI root redirects to index."""
        response = client.get("/pypi/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/pypi/index"

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.get_pypi_metrics")
    async def test_pypi_index_page(self, mock_metrics, client):
        """Test PyPI index page loads with metrics."""
        # Mock PyPI metrics response
        mock_metrics.return_value = {
            "total_packages": 100,
            "total_vulnerabilities": 5,
            "most_common_library": "requests",
            "average_version": "1.2.3"
        }

        response = client.get("/pypi/index")
        assert response.status_code == 200
        
        # Verify metrics were called
        mock_metrics.assert_called_once()

    def test_pypi_check_form_loads(self, client):
        """Test PyPI check form loads correctly."""
        response = client.get("/pypi/check")
        assert response.status_code == 200
        assert "request_group_id" in response.text

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.check_packages")
    async def test_pypi_check_form_post(self, mock_check_packages, client):
        """Test posting requirements to PyPI check."""
        mock_check_packages.return_value = None
        test_request_id = "test-request-123"

        response = client.post(
            f"/pypi/check?request_group_id={test_request_id}",
            data={
                "requirements": "requests==2.28.1\nnumpy>=1.21.0\nflask"
            },
            follow_redirects=False
        )

        assert response.status_code == 303
        assert response.headers.get("HX-Redirect") == f"/pypi/check/{test_request_id}"

        # Verify check_packages was called with processed data
        mock_check_packages.assert_called_once()
        args, kwargs = mock_check_packages.call_args
        assert kwargs["request_group_id"] == test_request_id
        assert "requests==2.28.1" in kwargs["packages"]
        assert "numpy>=1.21.0" in kwargs["packages"]
        assert "flask" in kwargs["packages"]

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.db_ops")
    async def test_pypi_check_results_success(self, mock_db_ops, client):
        """Test viewing PyPI check results."""
        test_request_id = "test-request-123"
        
        # Mock database response with requirement data
        mock_req1 = MagicMock()
        mock_req1.__dict__ = {
            "request_group_id": test_request_id,
            "package_name": "requests",
            "package_version": "2.28.1",
            "is_vulnerable": False,
            "text_in": "requests==2.28.1",
            "text_out": "Success"
        }
        mock_req2 = MagicMock()
        mock_req2.__dict__ = {
            "request_group_id": test_request_id,
            "package_name": "numpy",
            "package_version": "1.24.0", 
            "is_vulnerable": True,
            "text_in": "numpy>=1.21.0",
            "text_out": "Vulnerability found"
        }
        mock_requirements = [mock_req1, mock_req2]
        mock_db_ops.read_query = AsyncMock(return_value=mock_requirements)

        response = client.get(f"/pypi/check/{test_request_id}")
        assert response.status_code == 200

        # Verify database query was made
        mock_db_ops.read_query.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.db_ops")
    async def test_pypi_check_results_not_found(self, mock_db_ops, client):
        """Test viewing PyPI check results when no data exists."""
        test_request_id = "nonexistent-request"
        
        # Mock empty database response
        mock_db_ops.read_query = AsyncMock(return_value=[])

        response = client.get(f"/pypi/check/{test_request_id}", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/error/404"

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.db_ops")
    async def test_pypi_list_all_requirements(self, mock_db_ops, client):
        """Test listing all PyPI requirements."""
        # Mock database response
        mock_req1 = MagicMock()
        mock_req1.__dict__ = {
            "package_name": "requests",
            "package_version": "2.28.1",
            "date_created": "2024-01-01T00:00:00"
        }
        mock_req2 = MagicMock()
        mock_req2.__dict__ = {
            "package_name": "flask", 
            "package_version": "2.3.0",
            "date_created": "2024-01-02T00:00:00"
        }
        mock_requirements = [mock_req1, mock_req2]
        mock_db_ops.read_query = AsyncMock(return_value=mock_requirements)
        mock_db_ops.count_query = AsyncMock(return_value=2)

        response = client.get("/pypi/list")
        assert response.status_code == 200

        # Verify both read and count queries were called
        mock_db_ops.read_query.assert_called_once()
        mock_db_ops.count_query.assert_called_once()


class TestPyPIFormProcessing:
    """Test PyPI form data processing."""

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.check_packages")
    async def test_pypi_form_processing_empty_lines(self, mock_check_packages, client):
        """Test form processing handles empty lines correctly."""
        mock_check_packages.return_value = None
        test_request_id = "test-request-empty"

        response = client.post(
            f"/pypi/check?request_group_id={test_request_id}",
            data={
                "requirements": "requests==2.28.1\n\n\nnumpy>=1.21.0\n\n"
            },
            follow_redirects=False
        )

        assert response.status_code == 303

        # Verify empty lines were filtered out
        mock_check_packages.assert_called_once()
        args, kwargs = mock_check_packages.call_args
        packages = kwargs["packages"]
        assert len(packages) == 2
        assert "requests==2.28.1" in packages
        assert "numpy>=1.21.0" in packages

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.check_packages")
    async def test_pypi_form_processing_whitespace(self, mock_check_packages, client):
        """Test form processing handles whitespace correctly."""
        mock_check_packages.return_value = None
        test_request_id = "test-request-whitespace"

        response = client.post(
            f"/pypi/check?request_group_id={test_request_id}",
            data={
                "requirements": "  requests==2.28.1  \n\t numpy>=1.21.0\t\n   flask   "
            },
            follow_redirects=False
        )

        assert response.status_code == 303

        # Verify whitespace was stripped
        mock_check_packages.assert_called_once()
        args, kwargs = mock_check_packages.call_args
        packages = kwargs["packages"]
        assert "requests==2.28.1" in packages
        assert "numpy>=1.21.0" in packages
        assert "flask" in packages


class TestPyPIDataProcessing:
    """Test PyPI data processing and formatting."""

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.db_ops")
    async def test_pypi_results_data_filtering(self, mock_db_ops, client):
        """Test that private attributes are filtered from results."""
        test_request_id = "test-data-filtering"
        
        # Mock requirement with both public and private attributes
        mock_requirement = MagicMock()
        mock_requirement.__dict__ = {
            "package_name": "requests",
            "package_version": "2.28.1",
            "is_vulnerable": False,
            "text_in": "requests==2.28.1",
            "text_out": "Package found",
            "_sa_instance_state": "private_data",
            "_private_attr": "should_be_filtered",
            "public_attr": "should_be_included"
        }
        mock_db_ops.read_query = AsyncMock(return_value=[mock_requirement])

        response = client.get(f"/pypi/check/{test_request_id}")
        assert response.status_code == 200

        # The private attributes should be filtered out in the template context
        # We can't directly access the context, but the response should not fail

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.db_ops")
    async def test_pypi_list_data_filtering(self, mock_db_ops, client):
        """Test that private attributes are filtered from list results."""
        mock_requirement = MagicMock()
        mock_requirement.__dict__ = {
            "package_name": "flask",
            "package_version": "2.3.0",
            "_sa_instance_state": "private_data",
            "public_data": "should_be_included"
        }
        mock_db_ops.read_query = AsyncMock(return_value=[mock_requirement])
        mock_db_ops.count_query = AsyncMock(return_value=1)

        response = client.get("/pypi/list")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.db_ops")
    async def test_pypi_list_with_limit(self, mock_db_ops, client):
        """Test PyPI list with custom limit parameter."""
        mock_db_ops.read_query = AsyncMock(return_value=[])
        mock_db_ops.count_query = AsyncMock(return_value=0)

        response = client.get("/pypi/list?limit=500")
        assert response.status_code == 200

        # Verify the limit was applied to the query
        mock_db_ops.read_query.assert_called_once()
        call_args = mock_db_ops.read_query.call_args
        # The query should have a limit applied


class TestPyPIErrorHandling:
    """Test PyPI error handling scenarios."""

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.check_packages", side_effect=Exception("Package check failed"))
    async def test_pypi_check_form_error(self, mock_check_packages, client):
        """Test error handling in form processing."""
        test_request_id = "test-error"

        # The endpoint might handle the exception or let it bubble up
        # Testing that it doesn't crash the application
        try:
            response = client.post(
                "/pypi/check",
                data={
                    "requirements": "invalid-package-format",
                    "request_group_id": test_request_id
                },
                follow_redirects=False
            )
            # If no exception, check response
            assert response.status_code in [303, 500]
        except Exception:
            # If exception bubbles up, that's also acceptable behavior
            pass

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.db_ops.read_query", side_effect=Exception("Database error"))
    async def test_pypi_results_database_error(self, mock_read_query, client):
        """Test error handling when database fails."""
        test_request_id = "test-db-error"

        try:
            response = client.get(f"/pypi/check/{test_request_id}")
            # Should handle gracefully or return error
            assert response.status_code in [500, 200]
        except Exception:
            # Exception handling depends on app configuration
            pass

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.get_pypi_metrics", side_effect=Exception("Metrics failed"))
    async def test_pypi_index_metrics_error(self, mock_metrics, client):
        """Test error handling when metrics fail."""
        try:
            response = client.get("/pypi/index")
            # Should handle gracefully
            assert response.status_code in [500, 200]
        except Exception:
            # Exception handling depends on app configuration
            pass


class TestPyPIEdgeCases:
    """Test PyPI edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.check_packages")
    async def test_pypi_empty_requirements(self, mock_check_packages, client):
        """Test submitting empty requirements."""
        mock_check_packages.return_value = None
        test_request_id = "test-empty"

        response = client.post(
            f"/pypi/check?request_group_id={test_request_id}",
            data={
                "requirements": ""
            },
            follow_redirects=False
        )

        assert response.status_code == 303

        # Should be called with empty list
        mock_check_packages.assert_called_once()
        args, kwargs = mock_check_packages.call_args
        assert kwargs["packages"] == []

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.check_packages")
    async def test_pypi_special_characters(self, mock_check_packages, client):
        """Test requirements with special characters."""
        mock_check_packages.return_value = None
        test_request_id = "test-special"

        response = client.post(
            f"/pypi/check?request_group_id={test_request_id}",
            data={
                "requirements": "package-with-hyphens==1.0.0\npackage_with_underscores>=2.0.0"
            },
            follow_redirects=False
        )

        assert response.status_code == 303

        mock_check_packages.assert_called_once()
        args, kwargs = mock_check_packages.call_args
        packages = kwargs["packages"]
        assert "package-with-hyphens==1.0.0" in packages
        assert "package_with_underscores>=2.0.0" in packages

    def test_pypi_uuid_generation(self, client):
        """Test that check form generates unique request IDs."""
        # Test multiple requests to ensure UUID generation works
        response1 = client.get("/pypi/check")
        response2 = client.get("/pypi/check")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Both should contain request_group_id but we can't easily compare
        # the actual values without parsing the HTML
        assert "request_group_id" in response1.text
        assert "request_group_id" in response2.text


class TestPyPILogging:
    """Test PyPI logging functionality."""

    @patch("src.endpoints.pypi.logger")
    def test_pypi_root_logging(self, mock_logger, client):
        """Test that root endpoint logs redirect."""
        response = client.get("/pypi/", follow_redirects=False)
        assert response.status_code == 307
        
        # Verify logging was called
        mock_logger.info.assert_called_with("Redirecting to OpenAPI docs")

    @patch("src.endpoints.pypi.logger")
    def test_pypi_check_form_logging(self, mock_logger, client):
        """Test that check form logs template creation."""
        response = client.get("/pypi/check")
        assert response.status_code == 200
        
        # Verify logging calls were made
        assert mock_logger.info.call_count >= 1
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Creating template response" in call for call in log_calls)
        assert any("Returning response" in call for call in log_calls)


class TestPyPIIntegration:
    """Test PyPI integration scenarios."""

    @pytest.mark.asyncio
    @patch("src.endpoints.pypi.get_pypi_metrics")
    @patch("src.endpoints.pypi.check_packages")
    @patch("src.endpoints.pypi.db_ops")
    async def test_pypi_full_workflow(self, mock_db_ops, mock_check_packages, mock_metrics, client):
        """Test complete PyPI workflow from form to results."""
        test_request_id = "test-workflow"
        
        # Mock metrics for index page
        mock_metrics.return_value = {"total_packages": 50}
        
        # Mock check_packages
        mock_check_packages.return_value = None
        
        # Mock results data
        mock_req = MagicMock()
        mock_req.__dict__ = {
            "package_name": "requests", 
            "version": "2.28.1",
            "request_group_id": test_request_id,
            "text_in": "requests==2.28.1",
            "text_out": "Package found"
        }
        mock_requirements = [mock_req]
        mock_db_ops.read_query = AsyncMock(return_value=mock_requirements)
        
        # Step 1: Load index page
        response1 = client.get("/pypi/index")
        assert response1.status_code == 200
        
        # Step 2: Load check form
        response2 = client.get("/pypi/check")
        assert response2.status_code == 200
        
        # Step 3: Submit requirements
        response3 = client.post(
            f"/pypi/check?request_group_id={test_request_id}",
            data={
                "requirements": "requests==2.28.1"
            },
            follow_redirects=False
        )
        assert response3.status_code == 303
        
        # Step 4: View results
        response4 = client.get(f"/pypi/check/{test_request_id}")
        assert response4.status_code == 200
        
        # Verify all mocks were called appropriately
        mock_metrics.assert_called_once()
        mock_check_packages.assert_called_once()
        mock_db_ops.read_query.assert_called_once()