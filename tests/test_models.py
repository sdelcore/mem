"""Tests for Pydantic models."""

import unittest
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


class TestSource(unittest.TestCase):
    """Test Source model."""

    def test_source_creation(self):
        """Test creating a source."""
        source = Source(
            type="video",
            filename="test.mp4",
            start_timestamp=datetime.utcnow(),
        )
        self.assertEqual(source.type, "video")
        self.assertEqual(source.filename, "test.mp4")
        self.assertIsNone(source.location)
        self.assertIsNone(source.device_id)

    def test_source_with_all_fields(self):
        """Test source with all fields."""
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
        self.assertEqual(source.location, "office")
        self.assertAlmostEqual(source.duration_seconds, 100.5, places=1)
        self.assertEqual(source.metadata["fps"], 30.0)
        self.assertEqual(source.metadata["codec"], "h264")

    def test_source_type_validation(self):
        """Test source type validation."""
        with self.assertRaises(ValidationError):
            Source(
                type="invalid",  # Invalid type
                filename="test.mp4",
                start_timestamp=datetime.utcnow(),
            )


class TestFrame(unittest.TestCase):
    """Test Frame model."""

    def test_unique_frame_creation(self):
        """Test creating a unique frame."""
        now = datetime.utcnow()
        frame = Frame(
            source_id=1,
            first_seen_timestamp=now,
            last_seen_timestamp=now,
            perceptual_hash="abc123",
            image_data=b"fake_jpeg_data",
            metadata={"jpeg_quality": 85},
        )
        self.assertEqual(frame.source_id, 1)
        self.assertEqual(frame.perceptual_hash, "abc123")
        self.assertEqual(frame.size_bytes, 14)  # len(b"fake_jpeg_data")
        self.assertEqual(frame.metadata["jpeg_quality"], 85)

    def test_unique_frame_custom_quality(self):
        """Test unique frame with custom JPEG quality."""
        frame = Frame(
            source_id=1,
            first_seen_timestamp=datetime.utcnow(),
            last_seen_timestamp=datetime.utcnow(),
            perceptual_hash="hash",
            image_data=b"data",
            metadata={"jpeg_quality": 95, "reference_count": 5},
        )
        self.assertEqual(frame.metadata["jpeg_quality"], 95)
        self.assertEqual(frame.metadata.get("reference_count"), 5)


class TestTimeline(unittest.TestCase):
    """Test Timeline model."""

    def test_timeline_creation(self):
        """Test creating a timeline entry."""
        timeline = Timeline(
            source_id=1,
            timestamp=datetime.utcnow(),
        )
        self.assertEqual(timeline.source_id, 1)
        self.assertIsNone(timeline.frame_id)
        self.assertIsNone(timeline.transcription_id)
        self.assertEqual(timeline.similarity_score, 100.0)
        self.assertFalse(timeline.scene_changed)

    def test_timeline_with_all_fields(self):
        """Test timeline with all fields."""
        timeline = Timeline(
            entry_id=10,
            source_id=1,
            timestamp=datetime.utcnow(),
            frame_id=5,
            transcription_id=3,
            similarity_score=85.5,
            scene_changed=True,
        )
        self.assertEqual(timeline.frame_id, 5)
        self.assertEqual(timeline.similarity_score, 85.5)
        self.assertTrue(timeline.scene_changed)


class TestTranscription(unittest.TestCase):
    """Test Transcription model."""

    def test_transcription_creation(self):
        """Test creating a transcription."""
        now = datetime.utcnow()
        trans = Transcription(
            source_id=1,
            start_timestamp=now,
            end_timestamp=now,
            text="Hello world",
        )
        self.assertEqual(trans.source_id, 1)
        self.assertEqual(trans.text, "Hello world")
        self.assertEqual(trans.whisper_model, "base")

    def test_transcription_with_all_fields(self):
        """Test transcription with all fields."""
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
        self.assertEqual(trans.confidence, 0.95)
        self.assertEqual(trans.language, "en")
        self.assertEqual(trans.word_count, 2)
        self.assertEqual(trans.whisper_model, "large")


class TestFrameAnalysis(unittest.TestCase):
    """Test FrameAnalysis model."""

    def test_frame_analysis_creation(self):
        """Test creating frame analysis."""
        analysis = FrameAnalysis(
            frame_id=1,
            model_name="yolo",
            analysis_type="object_detection",
            result={"objects": ["person", "car"]},
        )
        self.assertEqual(analysis.frame_id, 1)
        self.assertEqual(analysis.model_name, "yolo")
        self.assertIn("objects", analysis.result)


class TestTranscriptAnalysis(unittest.TestCase):
    """Test TranscriptAnalysis model."""

    def test_transcript_analysis_creation(self):
        """Test creating transcript analysis."""
        analysis = TranscriptAnalysis(
            transcription_id=1,
            model_name="gpt",
            analysis_type="summary",
            result={"summary": "Brief summary"},
            processing_time_ms=150,
        )
        self.assertEqual(analysis.transcription_id, 1)
        self.assertEqual(analysis.processing_time_ms, 150)


class TestRequestResponseModels(unittest.TestCase):
    """Test request/response models."""

    def test_capture_video_request(self):
        """Test CaptureVideoRequest model."""
        request = CaptureVideoRequest(filepath="/path/to/video.mp4")
        self.assertEqual(request.filepath, "/path/to/video.mp4")
        self.assertEqual(request.frame_interval, 5)
        self.assertEqual(request.chunk_duration, 300)

        custom = CaptureVideoRequest(
            filepath="/path/to/video.mp4",
            frame_interval=10,
            chunk_duration=600,
        )
        self.assertEqual(custom.frame_interval, 10)

    def test_time_range_query(self):
        """Test TimeRangeQuery model."""
        now = datetime.utcnow()
        query = TimeRangeQuery(
            start=now,
            end=now,
        )
        self.assertIsNone(query.source_id)

        query_with_source = TimeRangeQuery(
            start=now,
            end=now,
            source_id=5,
        )
        self.assertEqual(query_with_source.source_id, 5)

    def test_frame_response(self):
        """Test FrameResponse model."""
        response = FrameResponse(
            id=1,
            source_id=2,
            timestamp=datetime.utcnow(),
            width=1920,
            height=1080,
            format="jpeg",
            size_bytes=50000,
        )
        self.assertEqual(response.id, 1)
        self.assertEqual(response.width, 1920)
        self.assertEqual(response.format, "jpeg")

    def test_transcription_response(self):
        """Test TranscriptionResponse model."""
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
        self.assertEqual(response.id, 1)
        self.assertEqual(response.text, "Sample text")
        self.assertEqual(response.confidence, 0.95)


if __name__ == "__main__":
    unittest.main()
