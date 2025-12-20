"""Tests for Pydantic models."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.storage.models import (
    Source,
    Frame,
    Timeline,
    Transcription,
    FrameAnalysis,
    TranscriptAnalysis,
    CaptureVideoRequest,
    TimeRangeQuery,
    FrameResponse,
    TranscriptionResponse,
)


class TestSource:
    def test_source_creation(self):
        source = Source(
            type="video",
            filename="test.mp4",
            start_timestamp=datetime.utcnow(),
        )
        assert source.type == "video"
        assert source.filename == "test.mp4"
        assert source.location is None
        assert source.device_id is None

    def test_source_with_all_fields(self):
        now = datetime.utcnow()
        source = Source(
            type="webcam",
            filename="capture.mp4",
            location="office",
            device_id="cam1",
            start_timestamp=now,
            end_timestamp=now + timedelta(seconds=100.5),
            metadata={"codec": "h264", "fps": 30.0, "width": 1920, "height": 1080},
        )
        assert source.location == "office"
        assert abs(source.duration_seconds - 100.5) < 0.1
        assert source.metadata["fps"] == 30.0
        assert source.metadata["codec"] == "h264"

    def test_source_type_validation(self):
        with pytest.raises(ValidationError):
            Source(
                type="invalid",
                filename="test.mp4",
                start_timestamp=datetime.utcnow(),
            )


class TestFrame:
    def test_unique_frame_creation(self):
        now = datetime.utcnow()
        frame = Frame(
            source_id=1,
            first_seen_timestamp=now,
            last_seen_timestamp=now,
            perceptual_hash="abc123",
            image_data=b"fake_jpeg_data",
            metadata={"jpeg_quality": 85},
        )
        assert frame.source_id == 1
        assert frame.perceptual_hash == "abc123"
        assert frame.size_bytes == 14
        assert frame.metadata["jpeg_quality"] == 85

    def test_unique_frame_custom_quality(self):
        frame = Frame(
            source_id=1,
            first_seen_timestamp=datetime.utcnow(),
            last_seen_timestamp=datetime.utcnow(),
            perceptual_hash="hash",
            image_data=b"data",
            metadata={"jpeg_quality": 95, "reference_count": 5},
        )
        assert frame.metadata["jpeg_quality"] == 95
        assert frame.metadata.get("reference_count") == 5


class TestTimeline:
    def test_timeline_creation(self):
        timeline = Timeline(
            source_id=1,
            timestamp=datetime.utcnow(),
        )
        assert timeline.source_id == 1
        assert timeline.frame_id is None
        assert timeline.transcription_id is None
        assert timeline.similarity_score == 100.0
        assert not timeline.scene_changed

    def test_timeline_with_all_fields(self):
        timeline = Timeline(
            entry_id=10,
            source_id=1,
            timestamp=datetime.utcnow(),
            frame_id=5,
            transcription_id=3,
            similarity_score=85.5,
            scene_changed=True,
        )
        assert timeline.frame_id == 5
        assert timeline.similarity_score == 85.5
        assert timeline.scene_changed


class TestTranscription:
    def test_transcription_creation(self):
        now = datetime.utcnow()
        trans = Transcription(
            source_id=1,
            start_timestamp=now,
            end_timestamp=now,
            text="Hello world",
        )
        assert trans.source_id == 1
        assert trans.text == "Hello world"
        assert trans.whisper_model == "base"

    def test_transcription_with_all_fields(self):
        now = datetime.utcnow()
        trans = Transcription(
            transcription_id=5,
            source_id=1,
            start_timestamp=now,
            end_timestamp=now,
            text="Test transcription",
            confidence=0.95,
            language="en",
            word_count=2,
            whisper_model="large",
        )
        assert trans.confidence == 0.95
        assert trans.language == "en"
        assert trans.word_count == 2
        assert trans.whisper_model == "large"


class TestFrameAnalysis:
    def test_frame_analysis_creation(self):
        analysis = FrameAnalysis(
            frame_id=1,
            model_name="yolo",
            analysis_type="object_detection",
            result={"objects": ["person", "car"]},
        )
        assert analysis.frame_id == 1
        assert analysis.model_name == "yolo"
        assert "objects" in analysis.result


class TestTranscriptAnalysis:
    def test_transcript_analysis_creation(self):
        analysis = TranscriptAnalysis(
            transcription_id=1,
            model_name="gpt",
            analysis_type="summary",
            result={"summary": "Brief summary"},
            processing_time_ms=150,
        )
        assert analysis.transcription_id == 1
        assert analysis.processing_time_ms == 150


class TestRequestResponseModels:
    def test_capture_video_request(self):
        request = CaptureVideoRequest(filepath="/path/to/video.mp4")
        assert request.filepath == "/path/to/video.mp4"
        assert request.frame_interval == 5
        assert request.chunk_duration == 300

        custom = CaptureVideoRequest(
            filepath="/path/to/video.mp4",
            frame_interval=10,
            chunk_duration=600,
        )
        assert custom.frame_interval == 10

    def test_time_range_query(self):
        now = datetime.utcnow()
        query = TimeRangeQuery(
            start=now,
            end=now,
        )
        assert query.source_id is None

        query_with_source = TimeRangeQuery(
            start=now,
            end=now,
            source_id=5,
        )
        assert query_with_source.source_id == 5

    def test_frame_response(self):
        response = FrameResponse(
            id=1,
            source_id=2,
            timestamp=datetime.utcnow(),
            width=1920,
            height=1080,
            format="jpeg",
            size_bytes=50000,
        )
        assert response.id == 1
        assert response.width == 1920
        assert response.format == "jpeg"

    def test_transcription_response(self):
        now = datetime.utcnow()
        response = TranscriptionResponse(
            id=1,
            source_id=2,
            start_timestamp=now,
            end_timestamp=now,
            text="Sample text",
            word_count=2,
            confidence=0.95,
            language="en",
        )
        assert response.id == 1
        assert response.text == "Sample text"
        assert response.confidence == 0.95
