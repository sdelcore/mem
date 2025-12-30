"""Audio transcription using STTD HTTP server."""

import logging
import re
import tempfile
import wave
from pathlib import Path
from typing import Any

from src.capture.sttd_client import (
    STTDClient,
    STTDConnectionError,
    STTDError,
    get_sttd_client,
)
from src.config import config

logger = logging.getLogger(__name__)


class Transcriber:
    """Handles audio transcription via STTD HTTP server."""

    def __init__(self, sttd_client: STTDClient | None = None):
        """Initialize transcriber with STTD HTTP client.

        Args:
            sttd_client: Optional STTD client instance. Uses global client if None.
        """
        self._client = sttd_client

    @property
    def client(self) -> STTDClient:
        """Get the STTD client, creating if needed."""
        if self._client is None:
            self._client = get_sttd_client()
        return self._client

    def transcribe_audio(
        self,
        audio_path: Path,
        language: str | None = None,
        identify_speakers: bool = True,
    ) -> dict[str, Any]:
        """Transcribe audio file via STTD server.

        Args:
            audio_path: Path to audio file.
            language: Optional language code (handled by server).
            identify_speakers: Whether to include speaker info (handled by server).

        Returns:
            Dictionary with transcription results.

        Raises:
            STTDConnectionError: If STTD server is not available.
            STTDError: If transcription fails.
        """
        logger.info(f"Transcribing audio via STTD server: {audio_path}")

        try:
            # Send to STTD server
            result = self.client.transcribe_file(audio_path)

            # Parse server response
            segments = result.get("segments", [])
            text = result.get("text", "")

            # Process segments to our format
            segments_list = []
            full_text = []

            for segment in segments:
                # Server returns segments with start, end, text, speaker, confidence
                start = segment.get("start", 0)
                end = segment.get("end", 0)
                segment_text = segment.get("text", "").strip()
                speaker = segment.get("speaker")
                speaker_confidence = segment.get("confidence")

                # Strip any speaker label prefix from text (e.g., "[Unknown]: ")
                if isinstance(segment_text, str):
                    segment_text = re.sub(r"^\[.*?\]:\s*", "", segment_text).strip()

                segment_dict = {
                    "start": start,
                    "end": end,
                    "text": segment_text,
                    "speaker": speaker,
                    "speaker_confidence": speaker_confidence,
                }
                segments_list.append(segment_dict)
                full_text.append(segment_text)

            combined_text = text if text else " ".join(full_text).strip()

            # Check for non-speech audio
            is_non_speech, audio_type = self.detect_non_speech_audio(
                {"text": combined_text, "segments": segments_list}
            )

            if is_non_speech:
                logger.info(f"Non-speech audio detected ({audio_type}): {audio_path}")
                return {
                    "text": audio_type,
                    "language": language or "en",
                    "segments": [{"text": audio_type, "start": 0, "end": 0}],
                    "is_non_speech": True,
                    "audio_type": audio_type,
                    "original_text": combined_text,
                }

            return {
                "text": combined_text,
                "language": language or "en",
                "segments": segments_list,
                "is_non_speech": False,
            }

        except STTDConnectionError as e:
            logger.error(f"STTD server not available: {e}")
            raise
        except STTDError as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def transcribe_chunk(
        self,
        audio_data: bytes,
        sample_rate: int = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Transcribe audio chunk from bytes.

        Args:
            audio_data: Raw audio bytes.
            sample_rate: Sample rate of audio (uses config default if None).
            language: Optional language code.

        Returns:
            Dictionary with transcription results.
        """
        if sample_rate is None:
            sample_rate = config.capture.audio.sample_rate

        # Save to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

            # Write WAV file
            with wave.open(str(tmp_path), "wb") as wav:
                wav.setnchannels(1)  # Mono
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(sample_rate)
                wav.writeframes(audio_data)

        try:
            return self.transcribe_audio(tmp_path, language)
        finally:
            # Clean up temp file
            tmp_path.unlink()

    def transcribe_with_timestamps(
        self, audio_path: Path, language: str | None = None
    ) -> dict[str, Any]:
        """Transcribe audio with timestamps.

        Args:
            audio_path: Path to audio file.
            language: Optional language code.

        Returns:
            Dictionary with transcription and timing information.
        """
        return self.transcribe_audio(audio_path, language)

    def health_check(self) -> bool:
        """Check if STTD server is available.

        Returns:
            True if server is healthy, False otherwise.
        """
        return self.client.health_check()

    def detect_non_speech_audio(self, result: dict) -> tuple[bool, str]:
        """Detect if audio is non-speech (music, noise, silence, etc).

        Returns:
            Tuple of (is_non_speech, description).
        """
        segments = result.get("segments", [])
        text = result.get("text", "").strip()

        # Analyze segments for non-speech indicators
        if segments:
            analysis = self.analyze_segments_for_speech(segments)

            if analysis["is_non_speech"]:
                audio_type = self.classify_non_speech_type(analysis, text)
                return True, audio_type

        # Fallback to pattern detection
        pattern_type = self.detect_non_speech_patterns(text)
        if pattern_type:
            return True, pattern_type

        return False, ""

    def analyze_segments_for_speech(self, segments: list) -> dict:
        """Analyze segments to determine if audio contains actual speech."""
        total_segments = len(segments)
        if total_segments == 0:
            return {"is_non_speech": True, "reason": "no_segments"}

        no_speech_count = 0
        low_confidence_count = 0
        high_compression_count = 0
        empty_text_count = 0
        short_segments_count = 0

        for segment in segments:
            if segment.get("no_speech_prob", 0) > 0.6:
                no_speech_count += 1

            if "avg_logprob" in segment and segment["avg_logprob"] < -1.0:
                low_confidence_count += 1

            if segment.get("compression_ratio", 1.0) > 2.5:
                high_compression_count += 1

            text = segment.get("text", "").strip()
            if not text:
                empty_text_count += 1
            elif len(text.split()) < 3:
                short_segments_count += 1

        no_speech_ratio = no_speech_count / total_segments
        low_confidence_ratio = low_confidence_count / total_segments
        empty_text_ratio = empty_text_count / total_segments

        is_non_speech = (
            no_speech_ratio > 0.5
            or low_confidence_ratio > 0.6
            or empty_text_ratio > 0.7
            or (high_compression_count > total_segments * 0.5)
        )

        return {
            "is_non_speech": is_non_speech,
            "no_speech_ratio": no_speech_ratio,
            "low_confidence_ratio": low_confidence_ratio,
            "empty_text_ratio": empty_text_ratio,
            "high_compression_count": high_compression_count,
            "short_segments_count": short_segments_count,
        }

    def classify_non_speech_type(self, analysis: dict, text: str) -> str:
        """Classify the type of non-speech audio based on analysis."""
        text_lower = text.lower()

        if any(pattern in text_lower for pattern in ["♪", "♫", "music", "singing", "song"]):
            return "[Music]"

        if any(pattern in text_lower for pattern in ["applause", "clapping", "cheering"]):
            return "[Applause]"

        if any(pattern in text_lower for pattern in ["laughter", "laughing", "haha"]):
            return "[Laughter]"

        if analysis.get("empty_text_ratio", 0) > 0.8:
            return "[Silence]"

        if analysis.get("no_speech_ratio", 0) > 0.7:
            return "[Background Noise]"

        if analysis.get("high_compression_count", 0) > 3:
            return "[Music]"

        return "[Non-Speech Audio]"

    def detect_non_speech_patterns(self, text: str) -> str:
        """Detect common non-speech patterns in transcribed text."""
        if not text:
            return "[Silence]"

        text_lower = text.lower()

        pattern_map = {
            "[Music]": ["♪", "♫", "[music]", "(music)", "[singing]", "[instrumental]"],
            "[Applause]": ["[applause]", "(applause)", "[clapping]", "(clapping)"],
            "[Laughter]": ["[laughter]", "(laughter)", "[laughing]", "haha", "hehe"],
            "[Background Noise]": ["[noise]", "(noise)", "[static]", "[wind]"],
            "[Silence]": ["[silence]", "(silence)", "[pause]"],
        }

        for description, patterns in pattern_map.items():
            if any(pattern in text_lower for pattern in patterns):
                return description

        # Check for repetitive nonsense
        words = text_lower.split()
        if words:
            unique_words = set(words)
            if len(words) > 3 and len(unique_words) < len(words) * 0.3:
                if all(len(word) <= 4 for word in unique_words) or all(
                    "%" in word for word in unique_words
                ):
                    return "[Repetitive Audio]"

            if all(word in ["la", "na", "da", "oh", "ah", "mm", "uh"] for word in words):
                return "[Music]"

        return ""

    def unload(self) -> None:
        """Clean up resources (no-op for HTTP client)."""
        logger.info("Transcriber cleanup complete")
