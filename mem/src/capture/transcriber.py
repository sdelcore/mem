"""Audio transcription using sttd with speaker diarization."""

import logging
import tempfile
import wave
from pathlib import Path
from typing import Any, Optional

import numpy as np

from src.config import config

logger = logging.getLogger(__name__)

# Try to import sttd, fallback to stub if not available
try:
    from sttd import (
        ProfileManager,
        SpeakerIdentifier,
        TranscriptionConfig,
    )
    from sttd import Transcriber as STTDTranscriber

    STTD_AVAILABLE = True
except ImportError:
    logger.warning("sttd not available, using fallback mode without speaker identification")
    STTD_AVAILABLE = False
    STTDTranscriber = None
    TranscriptionConfig = None
    SpeakerIdentifier = None
    ProfileManager = None


class Transcriber:
    """Handles audio transcription using sttd with speaker identification."""

    def __init__(
        self,
        model_name: str = None,
        device: str = None,
        compute_type: str = None,
        profiles_path: str = None,
    ):
        """
        Initialize transcriber with sttd.

        Args:
            model_name: Whisper model size (uses config default if None)
            device: Device to use - "cuda" or "cpu" (uses config default if None)
            compute_type: Compute type - "float16", "int8" (uses config default if None)
            profiles_path: Path to voice profiles directory
        """
        self.model_name = model_name or config.sttd.model
        self.device = device or config.sttd.device
        self.compute_type = compute_type or config.sttd.compute_type
        self.profiles_path = profiles_path or config.sttd.profiles_path

        self.transcriber = None
        self.identifier = None
        self.profile_manager = None

    def load_model(self):
        """Load the sttd transcriber and speaker identifier."""
        if self.transcriber is not None:
            return

        if not STTD_AVAILABLE:
            logger.warning("sttd not available, transcription will fail")
            return

        logger.info(f"Loading sttd model: {self.model_name}")

        sttd_config = TranscriptionConfig(
            model=self.model_name,
            device=self.device,
        )
        self.transcriber = STTDTranscriber(sttd_config)

        # Initialize speaker identification if enabled
        if config.sttd.speaker_identification:
            try:
                self.identifier = SpeakerIdentifier()
                profiles_dir = Path(self.profiles_path)
                profiles_dir.mkdir(parents=True, exist_ok=True)
                self.profile_manager = ProfileManager(profiles_dir)
                logger.info(f"Speaker identification enabled, profiles at {profiles_dir}")
            except Exception as e:
                logger.warning(f"Failed to initialize speaker identification: {e}")
                self.identifier = None
                self.profile_manager = None

        logger.info(f"sttd model loaded on {self.device}")

    def transcribe_audio(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        identify_speakers: bool = True,
    ) -> dict[str, Any]:
        """
        Transcribe audio file with optional speaker identification.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')
            identify_speakers: Whether to identify speakers

        Returns:
            Dictionary with transcription results
        """
        self.load_model()

        if not STTD_AVAILABLE or self.transcriber is None:
            error_msg = "sttd transcriber not available - ensure sttd is installed correctly"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(f"Transcribing audio: {audio_path}")

        # Force English language for transcription (matching original behavior)
        language = "en"
        logger.info("Forcing English language for transcription")

        # Get segments with timestamps using sttd
        segments = self.transcriber.transcribe_file_with_segments(str(audio_path))

        # Identify speakers if enabled and profiles exist
        if (
            identify_speakers
            and self.identifier
            and self.profile_manager
            and config.sttd.speaker_identification
        ):
            try:
                profiles = self.profile_manager.load_all()
                if profiles:
                    segments = self.identifier.identify_segments(
                        str(audio_path), segments, profiles
                    )
                    logger.info(f"Identified speakers using {len(profiles)} profiles")
            except Exception as e:
                logger.warning(f"Speaker identification failed: {e}")

        # Convert to our format
        segments_list = []
        full_text = []

        for segment in segments:
            # Handle both tuple format (start, end, text) and object format
            if isinstance(segment, tuple):
                start, end, text = segment
                speaker = None
                speaker_confidence = None
            else:
                start = getattr(segment, "start", 0)
                end = getattr(segment, "end", 0)
                text = getattr(segment, "text", "").strip()
                speaker = getattr(segment, "speaker", None)
                speaker_confidence = getattr(segment, "speaker_confidence", None)

            segment_dict = {
                "start": start,
                "end": end,
                "text": text.strip() if isinstance(text, str) else text,
                "speaker": speaker,
                "speaker_confidence": speaker_confidence,
            }
            segments_list.append(segment_dict)

            # Build text with speaker labels if available
            text_content = segment_dict["text"]
            if segment_dict["speaker"]:
                full_text.append(f"[{segment_dict['speaker']}]: {text_content}")
            else:
                full_text.append(text_content)

        combined_text = " ".join(full_text).strip()

        # Check if it's non-speech audio (always check for voice notes)
        if True:  # Always check for non-speech detection
            is_non_speech, audio_type = self.detect_non_speech_audio(
                {"text": combined_text, "segments": segments_list}
            )

            if is_non_speech:
                logger.info(f"Non-speech audio detected ({audio_type}): {audio_path}")
                return {
                    "text": audio_type,
                    "language": language,
                    "segments": [{"text": audio_type, "start": 0, "end": 0}],
                    "is_non_speech": True,
                    "audio_type": audio_type,
                    "original_text": combined_text,
                }

        return {
            "text": combined_text,
            "language": language,
            "segments": segments_list,
            "is_non_speech": False,
        }

    def transcribe_chunk(
        self,
        audio_data: bytes,
        sample_rate: int = None,
        language: Optional[str] = None,
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
            # Transcribe with speaker identification
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
        # sttd provides segment-level timestamps by default
        return self.transcribe_audio(audio_path, language)

    def detect_language(self, audio_path: Path) -> str:
        """
        Detect the language of audio.

        Args:
            audio_path: Path to audio file

        Returns:
            Detected language code
        """
        # For now, return English as default
        # sttd can be extended to support language detection
        return "en"

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
            elif "speaker_confidence" in segment and segment["speaker_confidence"]:
                total_prob += segment["speaker_confidence"]
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
        if any(
            pattern in text_lower for pattern in ["♪", "♫", "music", "singing", "song"]
        ):
            return "[Music]"

        if any(
            pattern in text_lower for pattern in ["applause", "clapping", "cheering"]
        ):
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
            if all(
                word in ["la", "na", "da", "oh", "ah", "mm", "uh"] for word in words
            ):
                return "[Music]"

        return ""

    def get_profile_manager(self) -> Optional["ProfileManager"]:
        """Get the profile manager for external use."""
        self.load_model()
        return self.profile_manager
