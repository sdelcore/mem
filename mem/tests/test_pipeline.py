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
        mock_config.capture.audio.chunk_duration_seconds = 60
        mock_config.capture.audio.overlap_seconds = 5
        mock_config.capture.frame.jpeg_quality = 85

        # Create config with no parameters
        config = CaptureConfig()

        # Check defaults are used
        assert config.frame_interval == 5
        assert config.chunk_duration == 60
        assert config.overlap_seconds == 5
        assert config.image_quality == 85

    @patch("src.capture.pipeline.app_config")
    def test_config_overrides(self, mock_config):
        """Test that CaptureConfig can override defaults."""
        # Set up mock config (these should be overridden)
        mock_config.capture.frame.interval_seconds = 5
        mock_config.capture.audio.chunk_duration_seconds = 60
        mock_config.capture.audio.overlap_seconds = 5
        mock_config.capture.frame.jpeg_quality = 85

        # Create config with custom parameters
        config = CaptureConfig(
            frame_interval=10,
            chunk_duration=120,
            overlap_seconds=10,
            image_quality=95,
        )

        # Check overrides are used
        assert config.frame_interval == 10
        assert config.chunk_duration == 120
        assert config.overlap_seconds == 10
        assert config.image_quality == 95

    @patch("src.capture.pipeline.app_config")
    def test_config_missing_overlap(self, mock_config):
        """Test config when overlap_seconds is not in config."""
        # Set up mock config without overlap_seconds
        mock_config.capture.frame.interval_seconds = 5
        mock_config.capture.frame.jpeg_quality = 85

        # Remove overlap_seconds attribute
        mock_audio = MagicMock()
        del mock_audio.overlap_seconds
        mock_audio.chunk_duration_seconds = 60
        mock_config.capture.audio = mock_audio

        # Create config
        config = CaptureConfig()

        # Check default of 5 is used when attribute missing (fallback from CaptureConfig)
        assert config.overlap_seconds == 5
