"""Shared pytest fixtures for the test suite."""

import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.storage.db import Database
from src.storage.models import (
    Source,
    Timeline,
    TimeframeAnnotation,
    Transcription,
    Frame,
)


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_db():
    """Create temporary test database."""
    # Create temporary database file
    db_path = f"/tmp/test_mem_{uuid.uuid4().hex}.duckdb"
    db = Database(db_path)

    try:
        db.connect()
        db.initialize()
        yield db
    finally:
        db.disconnect()
        # Clean up database file
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_source():
    """Create sample source data."""
    return Source(
        id=1,
        type="video",
        filename="2025-08-22_14-30-45.mp4",
        location="office",
        device_id="cam1",
        start_timestamp=datetime(2025, 8, 22, 14, 30, 45),
        end_timestamp=datetime(2025, 8, 22, 14, 35, 45),
        metadata={
            "fps": 30.0,
            "width": 1920,
            "height": 1080,
            "video_codec": "h264",
            "audio_codec": "aac",
            "duration": 300.0,
        },
    )


@pytest.fixture
def sample_frame():
    """Create sample frame data."""
    # Create a simple test image (1x1 red pixel)
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    jpeg_bytes = buffer.getvalue()

    return Frame(
        frame_id=1,
        source_id=1,
        first_seen_timestamp=datetime(2025, 8, 22, 14, 30, 50),
        last_seen_timestamp=datetime(2025, 8, 22, 14, 31, 50),
        perceptual_hash="abc123def456",
        image_data=jpeg_bytes,
        metadata={"jpeg_quality": 85, "width": 100, "height": 100},
    )


@pytest.fixture
def sample_timeline():
    """Create sample timeline entry."""
    return Timeline(
        entry_id=1,
        source_id=1,
        timestamp=datetime(2025, 8, 22, 14, 31, 0),
        frame_id=1,
        transcription_id=1,
        similarity_score=98.5,
    )


@pytest.fixture
def sample_transcription():
    """Create sample transcription data."""
    return Transcription(
        transcription_id=1,
        source_id=1,
        start_timestamp=datetime(2025, 8, 22, 14, 30, 45),
        end_timestamp=datetime(2025, 8, 22, 14, 31, 45),
        text="This is a test transcription for video processing.",
        confidence=0.95,
        language="en",
        word_count=8,
        model_name="whisper-base",
    )


@pytest.fixture
def mock_video_file(tmp_path):
    """Create a mock video file with correct naming."""
    video_path = tmp_path / "2025-08-22_14-30-45.mp4"
    video_path.write_bytes(b"fake video content")
    return str(video_path)


@pytest.fixture
def sample_annotation():
    """Create sample annotation data."""
    return TimeframeAnnotation(
        annotation_id=1,
        source_id=1,
        start_timestamp=datetime(2025, 8, 22, 14, 30, 0),
        end_timestamp=datetime(2025, 8, 22, 14, 35, 0),
        annotation_type="user_note",
        content="Important meeting discussion about Q3 results",
        metadata={"tags": ["meeting", "finance"], "importance": "high"},
        created_by="user123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def populated_db(test_db, sample_source, sample_frame, sample_timeline, sample_transcription):
    """Create a populated test database."""
    # Insert sample data
    source_id = test_db.create_source(sample_source)
    frame_id = test_db.store_frame(sample_frame)
    trans_id = test_db.store_transcription(sample_transcription)

    # Create timeline entry linking everything
    test_db.connection.execute(
        """
        INSERT INTO timeline (source_id, timestamp, frame_id, transcription_id, similarity_score)
        VALUES (?, ?, ?, ?, ?)
        """,
        [source_id, sample_timeline.timestamp, frame_id, trans_id, 98.5],
    )
    test_db.connection.commit()

    return test_db
