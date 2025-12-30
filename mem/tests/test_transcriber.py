"""Tests for the STTD-based transcriber module."""

import tempfile
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.capture.transcriber import Transcriber


@pytest.fixture
def mock_sttd_client():
    """Mock STTD client for testing."""
    client = MagicMock()
    client.health_check.return_value = True
    return client


@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)

        # Create a simple sine wave audio
        sample_rate = 16000
        duration = 1  # 1 second
        frequency = 440  # A4 note

        t = np.linspace(0, duration, sample_rate * duration)
        audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)

        with wave.open(str(tmp_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data.tobytes())

    yield tmp_path
    tmp_path.unlink()


class TestTranscriber:
    """Test cases for the Transcriber class."""

    def test_init_with_client(self, mock_sttd_client):
        """Test transcriber initialization with provided client."""
        transcriber = Transcriber(sttd_client=mock_sttd_client)
        assert transcriber.client == mock_sttd_client

    def test_init_lazy_client(self):
        """Test transcriber initialization without client uses lazy loading."""
        transcriber = Transcriber()
        assert transcriber._client is None

    @patch("src.capture.transcriber.get_sttd_client")
    def test_client_property_creates_client(self, mock_get_client):
        """Test that client property creates client on first access."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        transcriber = Transcriber()
        client = transcriber.client

        mock_get_client.assert_called_once()
        assert client == mock_client

    def test_transcribe_audio(self, mock_sttd_client, temp_audio_file):
        """Test audio transcription via STTD."""
        # Mock the transcribe result
        mock_sttd_client.transcribe_file.return_value = {
            "text": "Hello world",
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.0,
                    "text": "Hello world",
                    "speaker": "alice",
                    "confidence": 0.95,
                }
            ],
            "language": "en",
        }

        transcriber = Transcriber(sttd_client=mock_sttd_client)
        result = transcriber.transcribe_audio(temp_audio_file)

        assert result["text"] == "Hello world"
        assert result["language"] == "en"
        assert result["is_non_speech"] is False
        assert len(result["segments"]) == 1
        assert result["segments"][0]["text"] == "Hello world"
        assert result["segments"][0]["speaker"] == "alice"

    def test_transcribe_audio_non_speech(self, mock_sttd_client, temp_audio_file):
        """Test non-speech audio detection."""
        # Mock a segment that looks like music
        mock_sttd_client.transcribe_file.return_value = {
            "text": "♪♪♪",
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.0,
                    "text": "♪♪♪",
                    "no_speech_prob": 0.8,
                }
            ],
            "language": "en",
        }

        transcriber = Transcriber(sttd_client=mock_sttd_client)
        result = transcriber.transcribe_audio(temp_audio_file)

        assert result["is_non_speech"] is True
        assert result["audio_type"] == "[Music]"
        assert result["text"] == "[Music]"

    def test_transcribe_audio_strips_speaker_prefix(self, mock_sttd_client, temp_audio_file):
        """Test that speaker prefixes are stripped from text."""
        mock_sttd_client.transcribe_file.return_value = {
            "text": "[Unknown]: Hello there",
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.0,
                    "text": "[Unknown]: Hello there",
                    "speaker": None,
                }
            ],
            "language": "en",
        }

        transcriber = Transcriber(sttd_client=mock_sttd_client)
        result = transcriber.transcribe_audio(temp_audio_file)

        # Speaker prefix should be stripped from segment text
        assert result["segments"][0]["text"] == "Hello there"

    def test_health_check(self, mock_sttd_client):
        """Test health check passes through to client."""
        mock_sttd_client.health_check.return_value = True

        transcriber = Transcriber(sttd_client=mock_sttd_client)
        assert transcriber.health_check() is True
        mock_sttd_client.health_check.assert_called_once()

    def test_detect_non_speech_patterns(self):
        """Test non-speech pattern detection."""
        transcriber = Transcriber()

        # Test music patterns
        assert transcriber.detect_non_speech_patterns("♪♪♪") == "[Music]"
        assert transcriber.detect_non_speech_patterns("[music]") == "[Music]"

        # Test applause
        assert transcriber.detect_non_speech_patterns("[applause]") == "[Applause]"

        # Test laughter
        assert transcriber.detect_non_speech_patterns("haha") == "[Laughter]"

        # Test silence
        assert transcriber.detect_non_speech_patterns("") == "[Silence]"

        # Test repetitive audio
        assert transcriber.detect_non_speech_patterns("la la la la") == "[Repetitive Audio]"

        # Test normal text
        assert transcriber.detect_non_speech_patterns("Hello world") == ""

    def test_analyze_segments_for_speech(self):
        """Test segment analysis for speech detection."""
        transcriber = Transcriber()

        # Test with no segments
        result = transcriber.analyze_segments_for_speech([])
        assert result["is_non_speech"] is True
        assert result["reason"] == "no_segments"

        # Test with high no_speech probability
        segments = [
            {"no_speech_prob": 0.8, "text": "", "avg_logprob": -0.5},
            {"no_speech_prob": 0.9, "text": "", "avg_logprob": -0.5},
        ]
        result = transcriber.analyze_segments_for_speech(segments)
        assert result["is_non_speech"] is True
        assert result["no_speech_ratio"] == 1.0

        # Test with normal speech segments
        segments = [
            {"no_speech_prob": 0.1, "text": "Hello world", "avg_logprob": -0.3},
            {"no_speech_prob": 0.2, "text": "How are you", "avg_logprob": -0.4},
        ]
        result = transcriber.analyze_segments_for_speech(segments)
        assert result["is_non_speech"] is False

    def test_classify_non_speech_type(self):
        """Test classification of non-speech audio types."""
        transcriber = Transcriber()

        # Test music classification
        analysis = {"is_non_speech": True, "high_compression_count": 5}
        assert transcriber.classify_non_speech_type(analysis, "") == "[Music]"

        # Test silence classification
        analysis = {"is_non_speech": True, "empty_text_ratio": 0.9}
        assert transcriber.classify_non_speech_type(analysis, "") == "[Silence]"

        # Test background noise classification
        analysis = {"is_non_speech": True, "no_speech_ratio": 0.8}
        assert transcriber.classify_non_speech_type(analysis, "") == "[Background Noise]"

        # Test applause from text
        analysis = {"is_non_speech": True}
        assert transcriber.classify_non_speech_type(analysis, "[applause]") == "[Applause]"

    @patch("src.capture.transcriber.config")
    def test_transcribe_chunk(self, mock_config, mock_sttd_client):
        """Test transcribing audio chunks from bytes."""
        mock_config.capture.audio.sample_rate = 16000

        # Create audio data
        sample_rate = 16000
        duration = 1
        frequency = 440
        t = np.linspace(0, duration, sample_rate * duration)
        audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)

        # Mock transcribe result
        mock_sttd_client.transcribe_file.return_value = {
            "text": "Test audio",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Test audio", "speaker": None}
            ],
            "language": "en",
        }

        transcriber = Transcriber(sttd_client=mock_sttd_client)
        result = transcriber.transcribe_chunk(audio_data.tobytes())

        assert result["text"] == "Test audio"
        assert result["language"] == "en"
        assert result["is_non_speech"] is False

    def test_unload(self, mock_sttd_client):
        """Test unload is a no-op for HTTP client."""
        transcriber = Transcriber(sttd_client=mock_sttd_client)
        transcriber.unload()  # Should not raise
