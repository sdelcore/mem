"""Tests for API route endpoints."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns expected message."""
        response = test_client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Mem API is running"
        assert data["version"] == "1.0.0"


class TestCaptureEndpoint:
    """Test /api/capture endpoint."""

    def test_capture_valid_video(self, test_client, mock_video_file):
        """Test successful video capture request."""
        with patch("src.api.routes.capture_service.start_capture") as mock_capture:
            mock_capture.return_value = "job-123"
            with patch("src.api.routes.capture_service.get_job_status") as mock_status:
                mock_status.return_value = {
                    "job_id": "job-123",
                    "status": "processing",
                    "filepath": mock_video_file,
                }

                response = test_client.post("/api/capture", json={"filepath": mock_video_file})

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["job_id"] == "job-123"
                assert data["status"] == "processing"
                assert "Processing video" in data["message"]

    def test_capture_invalid_filename(self, test_client, tmp_path):
        """Test capture with invalid filename format."""
        # Create file with wrong naming format
        bad_file = tmp_path / "wrong_format.mp4"
        bad_file.write_bytes(b"fake")

        response = test_client.post("/api/capture", json={"filepath": str(bad_file)})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid filename format" in response.json()["detail"]

    def test_capture_missing_file(self, test_client):
        """Test capture with non-existent file."""
        response = test_client.post(
            "/api/capture", json={"filepath": "/nonexistent/2025-01-01_12-00-00.mp4"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "File not found" in response.json()["detail"]

    def test_capture_with_config(self, test_client, mock_video_file):
        """Test capture with custom configuration."""
        with patch("src.api.routes.capture_service.start_capture") as mock_capture:
            mock_capture.return_value = "job-456"
            with patch("src.api.routes.capture_service.get_job_status") as mock_status:
                mock_status.return_value = {"job_id": "job-456", "status": "processing"}

                config = {"frame_interval": 10, "jpeg_quality": 90}
                response = test_client.post(
                    "/api/capture", json={"filepath": mock_video_file, "config": config}
                )

                assert response.status_code == status.HTTP_200_OK
                mock_capture.assert_called_with(mock_video_file, config)


class TestSearchEndpoint:
    """Test /api/search endpoint."""

    def test_search_timeline_default(self, test_client, populated_db):
        """Test timeline search with default parameters."""
        with patch("src.api.routes.search_service.search_timeline") as mock_search:
            mock_search.return_value = {
                "count": 1,
                "entries": [
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "source_id": 1,
                        "scene_changed": False,
                        "frame": {
                            "frame_id": 1,
                            "perceptual_hash": "abc123",
                            "similarity_score": 98.5,
                        },
                        "transcript": {
                            "transcription_id": 1,
                            "text": "Test transcript",
                            "confidence": 0.95,
                        },
                    }
                ],
                "pagination": {"limit": 100, "offset": 0, "has_more": False},
            }

            response = test_client.get("/api/search?type=timeline")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["type"] == "timeline"
            assert data["count"] == 1
            assert len(data["entries"]) == 1

            # Verify default time range (last 24 hours)
            call_args = mock_search.call_args[0]
            assert (call_args[1] - call_args[0]).days >= 0  # end > start
            assert (datetime.utcnow() - call_args[1]).seconds < 60  # end is recent

    def test_search_timeline_with_range(self, test_client):
        """Test timeline search with specific time range."""
        start = "2025-08-22T14:30:00"
        end = "2025-08-22T15:30:00"

        with patch("src.api.routes.search_service.search_timeline") as mock_search:
            mock_search.return_value = {"count": 0, "entries": [], "pagination": None}

            response = test_client.get(f"/api/search?type=timeline&start={start}&end={end}")

            assert response.status_code == status.HTTP_200_OK
            call_args = mock_search.call_args[0]
            assert call_args[0] == datetime.fromisoformat(start)
            assert call_args[1] == datetime.fromisoformat(end)

    def test_search_frame_retrieval(self, test_client):
        """Test direct frame retrieval."""
        with patch("src.api.routes.search_service.get_frame") as mock_frame:
            mock_frame.return_value = (b"fake image data", "image/jpeg")

            response = test_client.get("/api/search?type=frame&frame_id=123")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "image/jpeg"
            assert response.headers["cache-control"] == "public, max-age=3600"
            assert b"fake image data" in response.content

    def test_search_frame_missing_id(self, test_client):
        """Test frame search without frame_id."""
        response = test_client.get("/api/search?type=frame")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "frame_id required" in response.json()["detail"]

    def test_search_transcripts(self, test_client):
        """Test transcript text search."""
        with patch("src.api.routes.search_service.search_transcripts") as mock_search:
            mock_search.return_value = {
                "count": 2,
                "results": [
                    {
                        "transcription_id": 1,
                        "source_id": 1,
                        "start_timestamp": datetime.utcnow().isoformat(),
                        "end_timestamp": datetime.utcnow().isoformat(),
                        "text": "Test transcript with search term",
                        "confidence": 0.95,
                        "language": "en",
                    }
                ],
                "pagination": {"limit": 100, "offset": 0, "has_more": False},
            }

            response = test_client.get("/api/search?type=transcript&q=search%20term")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["type"] == "transcript"
            assert data["count"] == 2
            assert len(data["results"]) == 1

    def test_search_transcript_missing_query(self, test_client):
        """Test transcript search without query text."""
        response = test_client.get("/api/search?type=transcript")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Query text 'q' required" in response.json()["detail"]

    def test_search_all_combined(self, test_client):
        """Test combined search (all type)."""
        with patch("src.api.routes.search_service.search_timeline") as mock_timeline:
            mock_timeline.return_value = {"count": 5, "entries": [], "pagination": None}
            with patch("src.api.routes.search_service.search_transcripts") as mock_trans:
                mock_trans.return_value = {
                    "count": 3,
                    "results": [],
                    "pagination": None,
                }

                response = test_client.get("/api/search?type=all&q=test")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["type"] == "all"
                assert data["count"] == 3  # timeline + transcripts
                assert "timeline" in data["results"]
                assert "transcripts" in data["results"]

    def test_search_invalid_type(self, test_client):
        """Test search with invalid type."""
        response = test_client.get("/api/search?type=invalid")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid search type" in response.json()["detail"]

    def test_search_with_pagination(self, test_client):
        """Test search with pagination parameters."""
        with patch("src.api.routes.search_service.search_timeline") as mock_search:
            mock_search.return_value = {
                "count": 150,
                "entries": [],
                "pagination": {"limit": 50, "offset": 50, "has_more": True},
            }

            response = test_client.get("/api/search?type=timeline&limit=50&offset=50")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["pagination"]["limit"] == 50
            assert data["pagination"]["offset"] == 50
            assert data["pagination"]["has_more"] is True


class TestStatusEndpoint:
    """Test /api/status endpoint."""

    def test_status_endpoint(self, test_client):
        """Test status endpoint returns system information."""
        with patch("src.api.routes.search_service.get_status") as mock_status:
            mock_status.return_value = {
                "system": {"version": "1.0.0", "uptime": 3600},
                "jobs": {"active": 2, "completed": 10, "failed": 1},
                "storage": {"total_frames": 1000, "total_transcriptions": 50},
                "sources": {"total": 5, "active": 1},
            }

            response = test_client.get("/api/status")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "system" in data
            assert "jobs" in data
            assert "storage" in data
            assert "sources" in data

    def test_status_error_handling(self, test_client):
        """Test status endpoint error handling."""
        with patch("src.api.routes.search_service.get_status") as mock_status:
            mock_status.side_effect = Exception("Database error")

            response = test_client.get("/api/status")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Database error" in response.json()["detail"]


class TestJobsEndpoint:
    """Test /api/jobs/{job_id} endpoint."""

    def test_get_job_status(self, test_client):
        """Test retrieving job status."""
        with patch("src.api.routes.capture_service.get_job_status") as mock_job:
            mock_job.return_value = {
                "job_id": "job-789",
                "status": "completed",
                "filepath": "/videos/test.mp4",
                "created_at": datetime.utcnow().isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
                "result": {"frames_extracted": 100, "transcriptions": 10},
            }

            response = test_client.get("/api/jobs/job-789")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["job_id"] == "job-789"
            assert data["status"] == "completed"
            assert "result" in data

    def test_get_job_not_found(self, test_client):
        """Test retrieving non-existent job."""
        with patch("src.api.routes.capture_service.get_job_status") as mock_job:
            mock_job.return_value = None

            response = test_client.get("/api/jobs/nonexistent")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Job nonexistent not found" in response.json()["detail"]


class TestErrorHandling:
    """Test global error handling."""

    def test_global_exception_handler(self, test_client):
        """Test that unhandled exceptions are caught."""
        with patch("src.api.routes.search_service.get_status") as mock_status:
            mock_status.side_effect = RuntimeError("Unexpected error")

            response = test_client.get("/api/status")

            # Should be caught by route-level handler first
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
