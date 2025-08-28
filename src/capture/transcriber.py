"""Audio transcription using Whisper."""

import builtins
import contextlib
import logging
import tempfile
import wave
from pathlib import Path
from typing import Any, Optional

import numpy as np

from src.config import config

try:
    import os
    import ssl

    import whisper

    # Handle SSL certificate issues for model downloads
    if os.environ.get("PYTHONHTTPSVERIFY", "1") == "0":
        ssl._create_default_https_context = ssl._create_unverified_context

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None

logger = logging.getLogger(__name__)


class Transcriber:
    """Handles audio transcription using Whisper."""

    def __init__(self, model_name: str = None, device: str = None):
        """
        Initialize transcriber.

        Args:
            model_name: Whisper model size (uses config default if None)
            device: Device to use (uses config default if None)
        """
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper is not installed. Run: pip install openai-whisper")

        self.model_name = model_name or config.whisper.model
        self.device = device or config.whisper.device
        self.model = None

    def load_model(self):
        """Load the Whisper model."""
        if self.model is None:
            logger.info(f"Loading Whisper model: {self.model_name}")

            # Temporarily disable SSL verification for model download if needed
            import ssl
            import urllib.request

            original_context = None
            try:
                original_context = urllib.request.ssl._create_default_https_context
                urllib.request.ssl._create_default_https_context = ssl._create_unverified_context
            except Exception:
                pass

            try:
                self.model = whisper.load_model(self.model_name, device=self.device)
                logger.info("Whisper model loaded successfully")
            finally:
                # Restore original SSL context if it was changed
                if original_context:
                    with contextlib.suppress(builtins.BaseException):
                        urllib.request.ssl._create_default_https_context = original_context

    def transcribe_audio(self, audio_path: Path, language: Optional[str] = None) -> dict[str, Any]:
        """
        Transcribe audio file with non-speech detection.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')

        Returns:
            Dictionary with transcription results
        """
        self.load_model()

        logger.info(f"Transcribing audio: {audio_path}")

        # Force English language for transcription
        language = "en"
        logger.info("Forcing English language for transcription")

        # Transcribe with settings that help detect non-speech
        result = self.model.transcribe(
            str(audio_path),
            language=language,
            verbose=False,
            no_speech_threshold=config.whisper.no_speech_threshold,
            logprob_threshold=config.whisper.logprob_threshold,
        )

        # Check if it's non-speech audio
        if config.whisper.detect_non_speech:
            is_non_speech, audio_type = self.detect_non_speech_audio(result)

            if is_non_speech:
                logger.info(f"Non-speech audio detected ({audio_type}): {audio_path}")
                return {
                    "text": audio_type,
                    "language": result.get("language", language),
                    "segments": [{"text": audio_type, "start": 0, "end": 0}],
                    "is_non_speech": True,
                    "audio_type": audio_type,
                    "original_text": result.get("text", ""),  # Keep for debugging
                }

        return {
            "text": result["text"].strip(),
            "language": result.get("language", language),
            "segments": result.get("segments", []),
            "is_non_speech": False,
        }

    def transcribe_chunk(
        self, audio_data: bytes, sample_rate: int = None, language: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Transcribe audio chunk from bytes with non-speech detection.

        Args:
            audio_data: Raw audio bytes
            sample_rate: Sample rate of audio (uses config default if None)
            language: Optional language code

        Returns:
            Dictionary with transcription results
        """
        if sample_rate is None:
            sample_rate = config.capture.audio.sample_rate

        self.load_model()

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

            # Write WAV file
            with wave.open(str(tmp_path), "wb") as wav:
                wav.setnchannels(1)  # Mono
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(sample_rate)
                wav.writeframes(audio_data)

        try:
            # Transcribe with non-speech detection
            result = self.transcribe_audio(tmp_path, language)
            return result
        finally:
            # Clean up temp file
            tmp_path.unlink()

    def transcribe_with_timestamps(
        self, audio_path: Path, language: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Transcribe audio with word-level timestamps.

        Args:
            audio_path: Path to audio file
            language: Optional language code

        Returns:
            Dictionary with transcription and timing information
        """
        self.load_model()

        logger.info(f"Transcribing with timestamps: {audio_path}")

        # Transcribe with timestamps
        result = self.model.transcribe(
            str(audio_path), language=language, verbose=False, word_timestamps=True
        )

        # Extract segments with timing
        segments = []
        for segment in result.get("segments", []):
            segments.append(
                {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "words": segment.get("words", []),
                }
            )

        return {
            "text": result["text"].strip(),
            "language": result.get("language", language),
            "segments": segments,
        }

    def detect_language(self, audio_path: Path) -> str:
        """
        Detect the language of audio.

        Args:
            audio_path: Path to audio file

        Returns:
            Detected language code
        """
        self.load_model()

        # Load audio
        audio = whisper.load_audio(str(audio_path))
        audio = whisper.pad_or_trim(audio)

        # Make log-Mel spectrogram
        mel = whisper.log_mel_spectrogram(audio).to(self.model.device)

        # Detect language
        _, probs = self.model.detect_language(mel)

        # Get most likely language
        language = max(probs, key=probs.get)
        logger.info(f"Detected language: {language} (confidence: {probs[language]:.2f})")

        return language

    def calculate_confidence(self, segments: list) -> float:
        """
        Calculate overall confidence score from segments.

        Args:
            segments: List of transcription segments

        Returns:
            Confidence score between 0 and 1
        """
        if not segments:
            return 0.0

        # Calculate average probability from segments
        total_prob = 0
        total_tokens = 0

        for segment in segments:
            if "avg_logprob" in segment:
                # Convert log probability to probability
                prob = np.exp(segment["avg_logprob"])
                # tokens might be a list, so get its length
                tokens = segment.get("tokens", [])
                if isinstance(tokens, list):
                    num_tokens = len(tokens)
                else:
                    num_tokens = int(tokens) if tokens else 1
                total_prob += prob * num_tokens
                total_tokens += num_tokens

        if total_tokens > 0:
            return min(total_prob / total_tokens, 1.0)
        return 0.5  # Default confidence

    def detect_non_speech_audio(self, result: dict) -> tuple[bool, str]:
        """
        Detect if audio is non-speech (music, noise, silence, etc).
        Returns (is_non_speech, description).
        """
        segments = result.get("segments", [])
        text = result.get("text", "").strip()

        # Analyze segments for non-speech indicators
        if segments:
            analysis = self.analyze_segments_for_speech(segments)

            # Determine type of non-speech audio
            if analysis["is_non_speech"]:
                audio_type = self.classify_non_speech_type(analysis, text)
                return True, audio_type

        # Fallback to pattern detection
        pattern_type = self.detect_non_speech_patterns(text)
        if pattern_type:
            return True, pattern_type

        return False, ""

    def analyze_segments_for_speech(self, segments: list) -> dict:
        """
        Analyze segments to determine if audio contains actual speech.
        """
        total_segments = len(segments)
        if total_segments == 0:
            return {"is_non_speech": True, "reason": "no_segments"}

        # Metrics for analysis
        no_speech_count = 0
        low_confidence_count = 0
        high_compression_count = 0
        empty_text_count = 0
        short_segments_count = 0

        for segment in segments:
            # High no_speech probability indicates non-speech
            if segment.get("no_speech_prob", 0) > 0.6:
                no_speech_count += 1

            # Very low confidence suggests non-speech or unclear audio
            if "avg_logprob" in segment and segment["avg_logprob"] < -1.0:
                low_confidence_count += 1

            # High compression ratio often indicates repetitive non-speech patterns
            if segment.get("compression_ratio", 1.0) > 2.5:
                high_compression_count += 1

            # Empty or very short text
            text = segment.get("text", "").strip()
            if not text:
                empty_text_count += 1
            elif len(text.split()) < 3:
                short_segments_count += 1

        # Calculate ratios
        no_speech_ratio = no_speech_count / total_segments
        low_confidence_ratio = low_confidence_count / total_segments
        empty_text_ratio = empty_text_count / total_segments

        # Determine if it's non-speech
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
        """
        Classify the type of non-speech audio based on analysis.
        """
        text_lower = text.lower()

        # Check for specific patterns in text
        if any(pattern in text_lower for pattern in ["♪", "♫", "music", "singing", "song"]):
            return "[Music]"

        if any(pattern in text_lower for pattern in ["applause", "clapping", "cheering"]):
            return "[Applause]"

        if any(pattern in text_lower for pattern in ["laughter", "laughing", "haha"]):
            return "[Laughter]"

        # High empty text ratio suggests silence or very quiet audio
        if analysis.get("empty_text_ratio", 0) > 0.8:
            return "[Silence]"

        # High no_speech ratio but some text might be ambient noise
        if analysis.get("no_speech_ratio", 0) > 0.7:
            return "[Background Noise]"

        # Repetitive patterns might be music or rhythmic sounds
        if analysis.get("high_compression_count", 0) > 3:
            return "[Music]"

        # Default to generic non-speech audio
        return "[Non-Speech Audio]"

    def detect_non_speech_patterns(self, text: str) -> str:
        """
        Detect common non-speech patterns in transcribed text.
        """
        if not text:
            return "[Silence]"

        text_lower = text.lower()

        # Map patterns to descriptions
        pattern_map = {
            "[Music]": ["♪", "♫", "[music]", "(music)", "[singing]", "[instrumental]"],
            "[Applause]": ["[applause]", "(applause)", "[clapping]", "(clapping)"],
            "[Laughter]": ["[laughter]", "(laughter)", "[laughing]", "haha", "hehe"],
            "[Background Noise]": ["[noise]", "(noise)", "[static]", "[wind]"],
            "[Silence]": ["[silence]", "(silence)", "[pause]"],
        }

        # Check each pattern category
        for description, patterns in pattern_map.items():
            if any(pattern in text_lower for pattern in patterns):
                return description

        # Check for repetitive nonsense (often from music/noise)
        words = text_lower.split()
        if words:
            unique_words = set(words)
            # High repetition of short words suggests non-speech
            if len(words) > 3 and len(unique_words) < len(words) * 0.3:
                # Check for repetitive patterns like "1.5%", numbers, or short words
                if all(len(word) <= 4 for word in unique_words) or all(
                    "%" in word for word in unique_words
                ):
                    return "[Repetitive Audio]"

            # Very short repeated sounds
            if all(word in ["la", "na", "da", "oh", "ah", "mm", "uh"] for word in words):
                return "[Music]"

        return ""
