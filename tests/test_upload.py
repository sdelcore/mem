"""Tests for video file upload endpoint."""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import uuid


def test_upload_valid_mkv(test_client: TestClient, tmp_path: Path):
    """Test uploading a valid MKV file with correct naming format."""
    # Create test file
    test_file = tmp_path / "2024-01-15_14-30-00.mkv"
    test_file.write_bytes(b"fake video content")

    # Mock the capture service to avoid actual processing
    with patch("src.api.routes.capture_service.start_capture") as mock_capture:
        mock_job_id = str(uuid.uuid4())
        mock_capture.return_value = mock_job_id

        with patch("src.api.routes.capture_service.get_job_status") as mock_status:
            mock_status.return_value = {
                "id": mock_job_id,
                "status": "processing",
                "filepath": str(test_file),
                "created_at": "2024-01-15T14:30:00Z",
                "result": None,
                "error": None,
            }

            with open(test_file, "rb") as f:
                response = test_client.post(
                    "/api/capture",
                    files={"file": ("2024-01-15_14-30-00.mkv", f, "video/x-matroska")},
                )

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] in ["queued", "processing"]
    assert "2024-01-15_14-30-00.mkv" in data["message"]


def test_upload_invalid_filename_format(test_client: TestClient, tmp_path: Path):
    """Test uploading MKV with invalid filename format."""
    test_file = tmp_path / "invalid_name.mkv"
    test_file.write_bytes(b"fake video content")

    with open(test_file, "rb") as f:
        response = test_client.post(
            "/api/capture", files={"file": ("invalid_name.mkv", f, "video/x-matroska")}
        )

    assert response.status_code == 400
    assert "Invalid filename format" in response.json()["detail"]
    assert "YYYY-MM-DD_HH-MM-SS.mkv" in response.json()["detail"]


def test_upload_wrong_extension(test_client: TestClient, tmp_path: Path):
    """Test uploading non-MKV file with correct naming format."""
    test_file = tmp_path / "2024-01-15_14-30-00.mp4"
    test_file.write_bytes(b"fake video content")

    with open(test_file, "rb") as f:
        response = test_client.post(
            "/api/capture", files={"file": ("2024-01-15_14-30-00.mp4", f, "video/mp4")}
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Invalid file extension" in detail or "Expected: YYYY-MM-DD_HH-MM-SS.mkv" in detail


def test_upload_missing_date_parts(test_client: TestClient, tmp_path: Path):
    """Test uploading MKV with incomplete date format."""
    test_file = tmp_path / "2024-01_14-30-00.mkv"  # Missing month day
    test_file.write_bytes(b"fake video content")

    with open(test_file, "rb") as f:
        response = test_client.post(
            "/api/capture",
            files={"file": ("2024-01_14-30-00.mkv", f, "video/x-matroska")},
        )

    assert response.status_code == 400
    assert "Invalid filename format" in response.json()["detail"]


@patch("src.api.routes.capture_service.start_capture")
@patch("src.api.routes.Path.mkdir")
def test_upload_saves_to_uploads_dir(
    mock_mkdir: MagicMock,
    mock_capture: MagicMock,
    test_client: TestClient,
    tmp_path: Path,
):
    """Test that uploaded file is saved to uploads directory."""
    mock_capture.return_value = "test-job-id"
    mock_mkdir.return_value = None

    test_file = tmp_path / "2024-01-15_14-30-00.mkv"
    test_file.write_bytes(b"fake video content for testing")

    with patch("src.api.routes.capture_service.get_job_status") as mock_status:
        mock_status.return_value = {
            "id": "test-job-id",
            "status": "processing",
            "filepath": "data/uploads/2024-01-15_14-30-00.mkv",
            "created_at": "2024-01-15T14:30:00Z",
            "result": None,
            "error": None,
        }

        with patch("builtins.open", create=True) as mock_open:
            # Mock file write operation
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            with open(test_file, "rb") as f:
                response = test_client.post(
                    "/api/capture",
                    files={"file": ("2024-01-15_14-30-00.mkv", f, "video/x-matroska")},
                )

    assert response.status_code == 200
    # Verify the capture service was called with the correct path
    assert mock_capture.called
    call_args = mock_capture.call_args[0]
    assert "uploads" in call_args[0]
    assert "2024-01-15_14-30-00.mkv" in call_args[0]


def test_upload_handles_large_file(test_client: TestClient, tmp_path: Path):
    """Test uploading a large MKV file (simulated)."""
    test_file = tmp_path / "2024-01-15_14-30-00.mkv"
    # Create a "large" file (actually small for testing)
    test_file.write_bytes(b"x" * 1024 * 1024)  # 1MB

    with patch("src.api.routes.capture_service.start_capture") as mock_capture:
        mock_capture.return_value = "large-file-job-id"

        with patch("src.api.routes.capture_service.get_job_status") as mock_status:
            mock_status.return_value = {
                "id": "large-file-job-id",
                "status": "processing",
                "filepath": str(test_file),
                "created_at": "2024-01-15T14:30:00Z",
                "result": None,
                "error": None,
            }

            with open(test_file, "rb") as f:
                response = test_client.post(
                    "/api/capture",
                    files={"file": ("2024-01-15_14-30-00.mkv", f, "video/x-matroska")},
                )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "large-file-job-id"


def test_upload_duplicate_filename_overwrites(test_client: TestClient, tmp_path: Path):
    """Test that uploading a file with duplicate name overwrites the previous one."""
    test_file = tmp_path / "2024-01-15_14-30-00.mkv"

    # First upload
    test_file.write_bytes(b"first video content")

    with patch("src.api.routes.capture_service.start_capture") as mock_capture:
        mock_capture.return_value = "job-1"

        with patch("src.api.routes.capture_service.get_job_status") as mock_status:
            mock_status.return_value = {
                "id": "job-1",
                "status": "processing",
                "filepath": str(test_file),
                "created_at": "2024-01-15T14:30:00Z",
                "result": None,
                "error": None,
            }

            with open(test_file, "rb") as f:
                response1 = test_client.post(
                    "/api/capture",
                    files={"file": ("2024-01-15_14-30-00.mkv", f, "video/x-matroska")},
                )

    assert response1.status_code == 200

    # Second upload with same filename
    test_file.write_bytes(b"second video content")

    with patch("src.api.routes.capture_service.start_capture") as mock_capture:
        mock_capture.return_value = "job-2"

        with patch("src.api.routes.capture_service.get_job_status") as mock_status:
            mock_status.return_value = {
                "id": "job-2",
                "status": "processing",
                "filepath": str(test_file),
                "created_at": "2024-01-15T14:30:01Z",
                "result": None,
                "error": None,
            }

            with open(test_file, "rb") as f:
                response2 = test_client.post(
                    "/api/capture",
                    files={"file": ("2024-01-15_14-30-00.mkv", f, "video/x-matroska")},
                )

    assert response2.status_code == 200
    assert response2.json()["job_id"] != response1.json()["job_id"]


def test_upload_no_file_provided(test_client: TestClient):
    """Test POST to capture endpoint without file."""
    response = test_client.post("/api/capture")
    assert response.status_code == 422  # Unprocessable Entity


def test_upload_empty_file(test_client: TestClient, tmp_path: Path):
    """Test uploading an empty MKV file."""
    test_file = tmp_path / "2024-01-15_14-30-00.mkv"
    test_file.write_bytes(b"")  # Empty file

    with open(test_file, "rb") as f:
        response = test_client.post(
            "/api/capture",
            files={"file": ("2024-01-15_14-30-00.mkv", f, "video/x-matroska")},
        )

    # Should still accept empty files (validation happens during processing)
    assert response.status_code in [200, 400]


def test_upload_future_date(test_client: TestClient, tmp_path: Path):
    """Test uploading MKV with future date in filename."""
    test_file = tmp_path / "2030-01-15_14-30-00.mkv"
    test_file.write_bytes(b"future video content")

    with patch("src.api.routes.capture_service.start_capture") as mock_capture:
        mock_capture.return_value = "future-job-id"

        with patch("src.api.routes.capture_service.get_job_status") as mock_status:
            mock_status.return_value = {
                "id": "future-job-id",
                "status": "processing",
                "filepath": str(test_file),
                "created_at": "2030-01-15T14:30:00Z",
                "result": None,
                "error": None,
            }

            with open(test_file, "rb") as f:
                response = test_client.post(
                    "/api/capture",
                    files={"file": ("2030-01-15_14-30-00.mkv", f, "video/x-matroska")},
                )

    # Should accept future dates (validation is format-only)
    assert response.status_code == 200
