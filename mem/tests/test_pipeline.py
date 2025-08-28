"""Tests for the pipeline module."""

import unittest
from unittest.mock import MagicMock, patch

from src.capture.pipeline import CaptureConfig


class TestCaptureConfig(unittest.TestCase):
    """Tests for CaptureConfig class."""

    @patch("src.capture.pipeline.app_config")
    def test_config_defaults(self, mock_config):
        """Test that CaptureConfig uses app config defaults."""
        # Set up mock config
        mock_config.capture.frame.interval_seconds = 5
        mock_config.capture.audio.chunk_duration_seconds = 300
        mock_config.capture.audio.overlap_seconds = 30
        mock_config.capture.frame.jpeg_quality = 85
        mock_config.whisper.model = "base"
        mock_config.whisper.language = "en"

        # Create config with no parameters
        config = CaptureConfig()

        # Check defaults are used
        assert config.frame_interval == 5
        assert config.chunk_duration == 300
        assert config.overlap_seconds == 30
        assert config.image_quality == 85
        assert config.whisper_model == "base"
        assert config.whisper_language == "en"

    @patch("src.capture.pipeline.app_config")
    def test_config_overrides(self, mock_config):
        """Test that CaptureConfig can override defaults."""
        # Set up mock config (these should be overridden)
        mock_config.capture.frame.interval_seconds = 5
        mock_config.capture.audio.chunk_duration_seconds = 300
        mock_config.capture.audio.overlap_seconds = 30
        mock_config.capture.frame.jpeg_quality = 85
        mock_config.whisper.model = "base"
        mock_config.whisper.language = "en"

        # Create config with custom parameters
        config = CaptureConfig(
            frame_interval=10,
            chunk_duration=600,
            overlap_seconds=60,
            image_quality=95,
            whisper_model="large",
            whisper_language="es",
        )

        # Check overrides are used
        assert config.frame_interval == 10
        assert config.chunk_duration == 600
        assert config.overlap_seconds == 60
        assert config.image_quality == 95
        assert config.whisper_model == "large"
        assert config.whisper_language == "es"

    @patch("src.capture.pipeline.app_config")
    def test_config_auto_language(self, mock_config):
        """Test that 'auto' language is converted to None."""
        # Set up mock config
        mock_config.capture.frame.interval_seconds = 5
        mock_config.capture.audio.chunk_duration_seconds = 300
        mock_config.capture.frame.jpeg_quality = 85
        mock_config.whisper.model = "base"
        mock_config.whisper.language = "auto"

        # Create config
        config = CaptureConfig()

        # Check 'auto' is converted to None
        assert config.whisper_language is None

    @patch("src.capture.pipeline.app_config")
    def test_config_missing_overlap(self, mock_config):
        """Test config when overlap_seconds is not in config."""
        # Set up mock config without overlap_seconds
        mock_config.capture.frame.interval_seconds = 5
        mock_config.capture.audio.chunk_duration_seconds = 300
        mock_config.capture.frame.jpeg_quality = 85
        mock_config.whisper.model = "base"
        mock_config.whisper.language = "en"

        # Remove overlap_seconds attribute
        mock_audio = MagicMock()
        del mock_audio.overlap_seconds
        mock_audio.chunk_duration_seconds = 300
        mock_config.capture.audio = mock_audio

        # Create config
        config = CaptureConfig()

        # Check default of 0 is used when attribute missing
        assert config.overlap_seconds == 0
