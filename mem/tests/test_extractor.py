"""Tests for the extractor module."""

import tempfile
import wave
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.capture.extractor import get_audio_chunks, parse_video_timestamp


class TestParseVideoTimestamp:
    """Tests for parse_video_timestamp function."""

    def test_valid_filename(self):
        """Test parsing valid filename format."""
        filename = "2025-08-22_14-30-45.mp4"
        result = parse_video_timestamp(filename)
        assert result == datetime(2025, 8, 22, 14, 30, 45)

    def test_invalid_filename_format(self):
        """Test parsing invalid filename format."""
        filename = "invalid_filename.mp4"
        try:
            parse_video_timestamp(filename)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid filename format" in str(e)

    def test_filename_without_extension(self):
        """Test parsing filename without extension."""
        filename = "2025-08-22_14-30-45"
        result = parse_video_timestamp(filename)
        assert result == datetime(2025, 8, 22, 14, 30, 45)


class TestGetAudioChunks:
    """Tests for get_audio_chunks function with overlap support."""

    def create_test_audio(
        self, duration_seconds: int = 10, sample_rate: int = 16000
    ) -> Path:
        """Create a test audio file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = Path(tmp.name)

        # Create test audio data
        num_frames = duration_seconds * sample_rate
        audio_data = b"\x00\x00" * num_frames  # Silent audio

        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)  # Mono
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data)

        return path

    def test_chunks_without_overlap(self):
        """Test audio chunking without overlap."""
        # Create 10 second audio file
        audio_path = self.create_test_audio(duration_seconds=10)

        try:
            chunks = list(
                get_audio_chunks(audio_path, chunk_duration=3, overlap_seconds=0)
            )

            # Should have 4 chunks: 0-3, 3-6, 6-9, 9-10
            assert len(chunks) == 4

            # Check first chunk
            assert chunks[0]["index"] == 0
            assert chunks[0]["start_seconds"] == 0.0
            assert chunks[0]["end_seconds"] == 3.0
            assert chunks[0]["has_overlap"] is False
            assert chunks[0]["overlap_start_seconds"] is None
            assert chunks[0]["overlap_end_seconds"] is None

            # Check second chunk (no overlap)
            assert chunks[1]["index"] == 1
            assert chunks[1]["start_seconds"] == 3.0
            assert chunks[1]["end_seconds"] == 6.0
            assert chunks[1]["has_overlap"] is False

            # Check last chunk
            assert chunks[3]["index"] == 3
            assert chunks[3]["start_seconds"] == 9.0
            assert chunks[3]["end_seconds"] == 10.0
            assert chunks[3]["has_overlap"] is False

        finally:
            audio_path.unlink()

    def test_chunks_with_overlap(self):
        """Test audio chunking with overlap."""
        # Create 10 second audio file
        audio_path = self.create_test_audio(duration_seconds=10)

        try:
            chunks = list(
                get_audio_chunks(audio_path, chunk_duration=5, overlap_seconds=1)
            )

            # With 5-second chunks and 1-second overlap, advancing by 4 seconds each time
            # Chunks: 0-5, 4-9, 8-10
            assert len(chunks) == 3

            # Check first chunk (no overlap before, has overlap after)
            assert chunks[0]["index"] == 0
            assert chunks[0]["start_seconds"] == 0.0
            assert chunks[0]["end_seconds"] == 5.0
            assert chunks[0]["has_overlap"] is True  # Has overlap with next chunk
            assert chunks[0]["overlap_start_seconds"] is None  # No previous overlap
            assert chunks[0]["overlap_end_seconds"] == 4.0  # Overlap starts at 4s

            # Check second chunk (has overlap before and after)
            assert chunks[1]["index"] == 1
            assert (
                chunks[1]["start_seconds"] == 4.0
            )  # Starts 1 second before previous chunk ended
            assert chunks[1]["end_seconds"] == 9.0
            assert chunks[1]["has_overlap"] is True
            assert chunks[1]["overlap_start_seconds"] == 4.0  # Overlaps with previous
            assert (
                chunks[1]["overlap_end_seconds"] == 8.0
            )  # Overlap with next starts at 8s

            # Check last chunk (has overlap before, no overlap after)
            assert chunks[2]["index"] == 2
            assert chunks[2]["start_seconds"] == 8.0
            assert chunks[2]["end_seconds"] == 10.0
            assert chunks[2]["has_overlap"] is True
            assert chunks[2]["overlap_start_seconds"] == 8.0  # Overlaps with previous
            assert chunks[2]["overlap_end_seconds"] is None  # No next chunk

        finally:
            audio_path.unlink()

    def test_chunks_with_large_overlap(self):
        """Test audio chunking with large overlap relative to chunk size."""
        # Create 10 second audio file
        audio_path = self.create_test_audio(duration_seconds=10)

        try:
            # Test with overlap equal to chunk duration (should fallback to no overlap)
            chunks = list(
                get_audio_chunks(audio_path, chunk_duration=3, overlap_seconds=3)
            )

            # Should behave like no overlap
            assert len(chunks) == 4
            assert chunks[0]["start_seconds"] == 0.0
            assert chunks[1]["start_seconds"] == 3.0
            assert chunks[2]["start_seconds"] == 6.0
            assert chunks[3]["start_seconds"] == 9.0

        finally:
            audio_path.unlink()

    @patch("src.capture.extractor.config")
    def test_chunks_with_config_defaults(self, mock_config):
        """Test audio chunking using config defaults."""
        # Mock config
        mock_config.capture.audio.chunk_duration_seconds = 5
        mock_config.capture.audio.overlap_seconds = 1

        # Create 10 second audio file
        audio_path = self.create_test_audio(duration_seconds=10)

        try:
            # Call without explicit parameters
            chunks = list(get_audio_chunks(audio_path))

            # Should use config defaults: 5-second chunks with 1-second overlap
            assert len(chunks) == 3
            assert chunks[0]["start_seconds"] == 0.0
            assert chunks[0]["end_seconds"] == 5.0
            assert chunks[1]["start_seconds"] == 4.0
            assert chunks[1]["end_seconds"] == 9.0

        finally:
            audio_path.unlink()

    def test_single_chunk(self):
        """Test when audio fits in a single chunk."""
        # Create 3 second audio file
        audio_path = self.create_test_audio(duration_seconds=3)

        try:
            chunks = list(
                get_audio_chunks(audio_path, chunk_duration=5, overlap_seconds=1)
            )

            # Should have only 1 chunk
            assert len(chunks) == 1
            assert chunks[0]["index"] == 0
            assert chunks[0]["start_seconds"] == 0.0
            assert chunks[0]["end_seconds"] == 3.0
            assert chunks[0]["has_overlap"] is False
            assert chunks[0]["overlap_start_seconds"] is None
            assert chunks[0]["overlap_end_seconds"] is None

        finally:
            audio_path.unlink()
