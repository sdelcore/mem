"""Tests for API service layer."""

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.api.services import CaptureService, SearchService


class TestCaptureService:
    """Test CaptureService class."""

    @pytest.fixture
    def capture_service(self):
        """Create CaptureService instance."""
        return CaptureService(db_path=":memory:")

    def test_start_capture_success(self, capture_service, mock_video_file):
        """Test successful capture job creation."""
        with patch("src.api.services.VideoCaptureProcessor") as mock_processor:
            mock_processor.return_value.process_video.return_value = {
                "status": "success",
                "source_id": 1,
                "frames_extracted": 50,
                "frames_stored": 45,
                "transcriptions": 5,
            }

            job_id = capture_service.start_capture(mock_video_file)

            assert job_id is not None
            assert len(job_id) == 36  # UUID format
            from src.api.services import JOBS

            assert job_id in JOBS

            # Check job was processed
            job = JOBS[job_id]
            assert job["status"] == "completed"
            assert job["filepath"] == mock_video_file
            assert job["result"]["frames_extracted"] == 50

    def test_start_capture_with_config(self, capture_service, mock_video_file):
        """Test capture with custom configuration."""
        config = {"frame_interval": 10, "chunk_duration": 300}

        with patch("src.api.services.CaptureConfig") as mock_config:
            with patch("src.api.services.VideoCaptureProcessor") as mock_processor:
                mock_processor.return_value.process_video.return_value = {
                    "status": "success",
                    "source_id": 1,
                    "frames_extracted": 30,
                }

                job_id = capture_service.start_capture(mock_video_file, config)

                # Verify config was created
                mock_config.assert_called_once()
                # Verify attributes were set on the config instance
                cfg_instance = mock_config.return_value
                assert cfg_instance.frame_interval == 10
                assert cfg_instance.chunk_duration == 300

    def test_start_capture_failure(self, capture_service, mock_video_file):
        """Test capture job failure handling."""
        with patch("src.api.services.VideoCaptureProcessor") as mock_processor:
            mock_processor.return_value.process_video.side_effect = Exception(
                "Processing failed"
            )

            job_id = capture_service.start_capture(mock_video_file)

            # Check job marked as failed
            from src.api.services import JOBS

            job = JOBS[job_id]
            assert job["status"] == "failed"
            assert job["error"] == "Processing failed"
            assert job["completed_at"] is not None

    def test_get_job_status_exists(self, capture_service):
        """Test retrieving existing job status."""
        # Manually create a job
        from src.api.services import JOBS

        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "filepath": "/test/video.mp4",
        }

        status = capture_service.get_job_status(job_id)

        assert status is not None
        assert status["job_id"] == job_id
        assert status["status"] == "processing"

    def test_get_job_status_not_found(self, capture_service):
        """Test retrieving non-existent job status."""
        status = capture_service.get_job_status("nonexistent")
        assert status is None


class TestSearchService:
    """Test SearchService class."""

    @pytest.fixture
    def search_service(self, test_db):
        """Create SearchService instance with test database."""
        service = SearchService(db_path=test_db.db_path)
        service.db = test_db  # Use existing connection
        return service

    def test_search_timeline(self, search_service, populated_db):
        """Test timeline search functionality."""
        start = datetime(2025, 8, 22, 14, 30, 0)
        end = datetime(2025, 8, 22, 14, 35, 0)

        result = search_service.search_timeline(start, end)

        assert "count" in result
        assert "entries" in result
        assert "pagination" in result
        assert result["count"] >= 0
        assert isinstance(result["entries"], list)

    def test_search_timeline_with_source(self, search_service, populated_db):
        """Test timeline search with source filter."""
        start = datetime(2025, 8, 22, 14, 30, 0)
        end = datetime(2025, 8, 22, 14, 35, 0)

        result = search_service.search_timeline(start, end, source_id=1)

        assert result["count"] >= 0
        # All entries should be from source_id=1
        for entry in result["entries"]:
            assert entry["source_id"] == 1

    def test_search_timeline_pagination(self, search_service, populated_db):
        """Test timeline search pagination."""
        start = datetime(2025, 8, 22, 14, 0, 0)
        end = datetime(2025, 8, 22, 15, 0, 0)

        result = search_service.search_timeline(start, end, limit=10, offset=5)

        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["offset"] == 5
        assert "has_more" in result["pagination"]

    def test_get_frame(self, search_service, populated_db, sample_frame):
        """Test frame retrieval."""
        # Store a frame first
        frame_id = populated_db.store_unique_frame(sample_frame)

        image_data, content_type = search_service.get_frame(frame_id)

        assert image_data is not None
        assert len(image_data) > 0
        assert content_type == "image/jpeg"

    def test_get_frame_with_resize(self, search_service, populated_db, sample_frame):
        """Test frame retrieval with resizing."""
        frame_id = populated_db.store_unique_frame(sample_frame)

        image_data, content_type = search_service.get_frame(
            frame_id, format="jpeg", size="640x480"
        )

        assert image_data is not None
        # Image should be different size after resize
        assert len(image_data) > 0

    def test_get_frame_png_format(self, search_service, populated_db, sample_frame):
        """Test frame retrieval as PNG."""
        frame_id = populated_db.store_unique_frame(sample_frame)

        image_data, content_type = search_service.get_frame(frame_id, format="png")

        assert content_type == "image/png"
        # PNG should start with PNG signature
        assert image_data[:4] == b"\x89PNG"

    def test_get_frame_not_found(self, search_service):
        """Test frame retrieval for non-existent frame."""
        with pytest.raises(ValueError, match="Frame 9999 not found"):
            search_service.get_frame(9999)

    def test_search_transcripts(self, search_service, populated_db):
        """Test transcript text search."""
        result = search_service.search_transcripts("test")

        assert "count" in result
        assert "results" in result
        assert "pagination" in result
        assert isinstance(result["results"], list)

    def test_search_transcripts_with_source(self, search_service, populated_db):
        """Test transcript search with source filter."""
        result = search_service.search_transcripts("test", source_id=1)

        # All results should be from source_id=1
        for transcript in result["results"]:
            assert transcript["source_id"] == 1

    def test_search_transcripts_pagination(self, search_service, populated_db):
        """Test transcript search pagination."""
        result = search_service.search_transcripts("test", limit=5, offset=2)

        assert result["pagination"]["limit"] == 5
        assert result["pagination"]["offset"] == 2

    def test_get_status(self, search_service, populated_db):
        """Test system status retrieval."""
        # Mock the JOBS global
        with patch("src.api.services.JOBS") as mock_jobs:
            mock_jobs.items.return_value = [
                ("job1", {"status": "completed"}),
                ("job2", {"status": "processing"}),
                ("job3", {"status": "failed"}),
            ]

            status = search_service.get_status()

            assert "system" in status
            assert "jobs" in status
            assert "storage" in status
            assert "sources" in status

            assert status["jobs"]["active"] == 1
            assert status["jobs"]["completed"] == 1
            assert status["jobs"]["failed"] == 1

    def test_get_status_empty_database(self, search_service, test_db):
        """Test status with empty database."""
        with patch("src.api.services.JOBS") as mock_jobs:
            mock_jobs.items.return_value = []

            status = search_service.get_status()

            assert status["jobs"]["active"] == 0
            assert status["jobs"]["completed"] == 0
            assert status["jobs"]["failed"] == 0
            assert status["storage"]["frames"]["total"] >= 0


class TestServiceIntegration:
    """Test service integration scenarios."""

    def test_capture_and_search_workflow(self, test_db, mock_video_file):
        """Test complete capture and search workflow."""
        capture_service = CaptureService(db_path=test_db.db_path)
        search_service = SearchService(db_path=test_db.db_path)

        # Mock the processor to simulate successful capture
        with patch("src.api.services.VideoCaptureProcessor") as mock_processor:
            mock_processor.return_value.process_video.return_value = {
                "source_id": 1,
                "frames_extracted": 10,
                "frames_stored": 8,
                "transcriptions": 2,
            }

            # Start capture
            job_id = capture_service.start_capture(mock_video_file)
            job = capture_service.get_job_status(job_id)
            assert job["status"] == "completed"

            # Now search for the captured data
            with patch.object(search_service, "db", test_db):
                # Create some test data for search
                from src.storage.models import Source

                source = Source(
                    filename="2025-08-22_14-30-45.mp4",
                    location=mock_video_file,
                    source_type="video",
                    start_timestamp=datetime.utcnow(),
                    duration_seconds=300,
                )
                test_db.create_source(source)

                # Search timeline
                result = search_service.search_timeline(
                    datetime.utcnow() - timedelta(hours=1), datetime.utcnow()
                )
                assert result is not None
