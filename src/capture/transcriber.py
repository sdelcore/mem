"""Audio transcription using Whisper."""

import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import wave
import numpy as np

from src.config import config

try:
    import whisper
    import ssl
    import os

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
            except:
                pass

            try:
                self.model = whisper.load_model(self.model_name, device=self.device)
                logger.info("Whisper model loaded successfully")
            finally:
                # Restore original SSL context if it was changed
                if original_context:
                    try:
                        urllib.request.ssl._create_default_https_context = original_context
                    except:
                        pass

    def transcribe_audio(self, audio_path: Path, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')

        Returns:
            Dictionary with transcription results
        """
        self.load_model()

        logger.info(f"Transcribing audio: {audio_path}")

        # Transcribe
        result = self.model.transcribe(str(audio_path), language=language, verbose=False)

        return {
            "text": result["text"].strip(),
            "language": result.get("language", language),
            "segments": result.get("segments", []),
        }

    def transcribe_chunk(
        self, audio_data: bytes, sample_rate: int = None, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio chunk from bytes.

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
            # Transcribe
            result = self.transcribe_audio(tmp_path, language)
            return result
        finally:
            # Clean up temp file
            tmp_path.unlink()

    def transcribe_with_timestamps(
        self, audio_path: Path, language: Optional[str] = None
    ) -> Dict[str, Any]:
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
