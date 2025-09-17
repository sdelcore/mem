"""Audio transcription using Faster-Whisper."""

import logging
import tempfile
import wave
from pathlib import Path
from typing import Any, Optional

import numpy as np
from faster_whisper import WhisperModel

from src.config import config

logger = logging.getLogger(__name__)


class Transcriber:
    """Handles audio transcription using Faster-Whisper."""

    def __init__(self, model_name: str = None, device: str = None, compute_type: str = None):
        """
        Initialize transcriber with Faster-Whisper.

        Args:
            model_name: Whisper model size (uses config default if None)
            device: Device to use - "cuda" or "cpu" (uses config default if None)
            compute_type: Compute type - "float16", "int8", "int8_float16" (uses config default if None)
        """
        self.model_name = model_name or config.whisper.model
        self.device = device or config.whisper.device
        # Faster-whisper specific: compute type for quantization
        self.compute_type = compute_type or getattr(config.whisper, "compute_type", "float16")
        self.model = None

    def load_model(self):
        """Load the Faster-Whisper model."""
        if self.model is None:
            logger.info(f"Loading Faster-Whisper model: {self.model_name}")

            # Faster-whisper uses different initialization
            # Models are downloaded to ~/.cache/huggingface by default
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=4,  # Number of threads when running on CPU
                num_workers=1,  # Number of workers for preprocessing
            )
            logger.info(f"Faster-Whisper model loaded successfully on {self.device}")

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

        # Transcribe with Faster-Whisper
        # Returns generator of segments and info dict
        segments_generator, info = self.model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            best_of=5,
            patience=1,
            length_penalty=1,
            temperature=0,
            compression_ratio_threshold=2.4,
            log_prob_threshold=config.whisper.logprob_threshold,
            no_speech_threshold=config.whisper.no_speech_threshold,
            condition_on_previous_text=True,
            initial_prompt=None,
            prefix=None,
            suppress_blank=True,
            suppress_tokens=[-1],
            without_timestamps=False,
            max_initial_timestamp=1.0,
            word_timestamps=False,
            prepend_punctuations='"\'"¿([{-',
            append_punctuations='"\'.。,，!！?？:：")]}、',
            vad_filter=True,  # Voice Activity Detection filter
            vad_parameters=dict(
                threshold=0.5,
                min_speech_duration_ms=250,
                max_speech_duration_s=float("inf"),
                min_silence_duration_ms=2000,
                window_size_samples=1024,
                speech_pad_ms=400,
            ),
        )

        # Convert generator to list and extract text
        segments_list = []
        full_text = []

        for segment in segments_generator:
            segment_dict = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "no_speech_prob": segment.no_speech_prob,
                "avg_logprob": segment.avg_logprob,
                "compression_ratio": segment.compression_ratio,
            }
            segments_list.append(segment_dict)
            full_text.append(segment.text.strip())

        combined_text = " ".join(full_text).strip()

        # Check if it's non-speech audio
        if config.whisper.detect_non_speech:
            is_non_speech, audio_type = self.detect_non_speech_audio(
                {"text": combined_text, "segments": segments_list}
            )

            if is_non_speech:
                logger.info(f"Non-speech audio detected ({audio_type}): {audio_path}")
                return {
                    "text": audio_type,
                    "language": info.language if info else language,
                    "segments": [{"text": audio_type, "start": 0, "end": 0}],
                    "is_non_speech": True,
                    "audio_type": audio_type,
                    "original_text": combined_text,  # Keep for debugging
                }

        return {
            "text": combined_text,
            "language": info.language if info else language,
            "segments": segments_list,
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

        # Transcribe with word timestamps enabled
        segments_generator, info = self.model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,  # Enable word-level timestamps
            vad_filter=True,
        )

        # Extract segments with timing
        segments = []
        full_text = []

        for segment in segments_generator:
            words = []
            if segment.words:
                words = [
                    {
                        "start": word.start,
                        "end": word.end,
                        "word": word.word,
                        "probability": word.probability,
                    }
                    for word in segment.words
                ]

            segments.append(
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "words": words,
                }
            )
            full_text.append(segment.text.strip())

        return {
            "text": " ".join(full_text).strip(),
            "language": info.language if info else language,
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

        # Faster-whisper language detection
        # Transcribe a short segment to detect language
        segments, info = self.model.transcribe(
            str(audio_path),
            beam_size=1,
            best_of=1,
            temperature=0,
            without_timestamps=True,
            max_initial_timestamp=10.0,  # Only analyze first 10 seconds
            condition_on_previous_text=False,
        )

        # Get detected language from info
        detected_language = info.language if info else "unknown"
        language_probability = info.language_probability if info else 0.0

        logger.info(
            f"Detected language: {detected_language} (confidence: {language_probability:.2f})"
        )

        return detected_language

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
        total_segments = 0

        for segment in segments:
            if "avg_logprob" in segment:
                # Convert log probability to probability
                prob = np.exp(segment["avg_logprob"])
                total_prob += prob
                total_segments += 1

        if total_segments > 0:
            return min(total_prob / total_segments, 1.0)
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
