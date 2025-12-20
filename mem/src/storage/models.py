"""Pydantic models for database entities."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Represents a video/stream source."""

    id: Optional[int] = None
    type: str = Field(..., pattern="^(video|stream|webcam|user_recording)$")
    filename: str
    location: Optional[str] = None  # 'front_door', 'office', etc.
    device_id: Optional[str] = None  # Camera identifier
    start_timestamp: datetime
    end_timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = (
        None  # Contains fps, width, height, duration, etc.
    )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Computed duration in seconds."""
        if self.end_timestamp and self.start_timestamp:
            return (self.end_timestamp - self.start_timestamp).total_seconds()
        return None


class Frame(BaseModel):
    """Represents a frame with optional perceptual hash deduplication."""

    frame_id: Optional[int] = None
    source_id: int
    first_seen_timestamp: datetime
    last_seen_timestamp: datetime
    perceptual_hash: str  # For similarity detection
    image_data: bytes  # JPEG compressed image
    metadata: Optional[dict[str, Any]] = (
        None  # Contains jpeg_quality, processing params, etc.
    )

    @property
    def size_bytes(self) -> int:
        """Computed size of image data."""
        return len(self.image_data) if self.image_data else 0


class Timeline(BaseModel):
    """Maps timestamps to frames and transcriptions."""

    entry_id: Optional[int] = None
    source_id: int
    timestamp: datetime
    frame_id: Optional[int] = None
    transcription_id: Optional[int] = None
    similarity_score: Optional[float] = 100.0  # 0-100, similarity to previous frame

    @property
    def scene_changed(self) -> bool:
        """Computed scene change flag based on similarity score."""
        return (
            self.similarity_score < 95.0 if self.similarity_score is not None else False
        )


class Transcription(BaseModel):
    """Represents an audio transcription segment."""

    transcription_id: Optional[int] = None
    source_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    text: str
    confidence: Optional[float] = None
    language: Optional[str] = None
    whisper_model: str = "base"
    has_overlap: bool = False  # Whether this chunk has overlap regions
    overlap_start: Optional[datetime] = None  # Start of overlap with previous chunk
    overlap_end: Optional[datetime] = None  # End of overlap with next chunk
    # Speaker identification fields (sttd diarization)
    speaker_id: Optional[int] = None  # Reference to speaker_profiles
    speaker_name: Optional[str] = None  # Speaker name at time of transcription
    speaker_confidence: Optional[float] = None  # Confidence of speaker ID (0-1)

    @property
    def word_count(self) -> int:
        """Computed word count from text."""
        return len(self.text.split()) if self.text else 0


class SpeakerProfile(BaseModel):
    """Represents a registered speaker voice profile for diarization."""

    profile_id: Optional[int] = None
    name: str  # Unique identifier (e.g., 'alice', 'bob')
    display_name: Optional[str] = None  # Human-readable name
    audio_sample: Optional[bytes] = None  # Original registration audio
    embedding_data: Optional[bytes] = None  # sttd speaker embedding
    metadata: Optional[dict[str, Any]] = None  # Additional profile data
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FrameAnalysis(BaseModel):
    """Represents analysis results for a frame."""

    id: Optional[int] = None
    frame_id: int
    model_name: str
    analysis_type: str
    result: dict[str, Any]
    processing_time_ms: Optional[int] = None
    created_at: Optional[datetime] = None


class TranscriptAnalysis(BaseModel):
    """Represents analysis results for a transcript."""

    id: Optional[int] = None
    transcription_id: int
    model_name: str
    analysis_type: str
    result: dict[str, Any]
    processing_time_ms: Optional[int] = None
    created_at: Optional[datetime] = None


class TimeframeAnnotation(BaseModel):
    """Represents an annotation for a specific timeframe."""

    annotation_id: Optional[int] = None
    source_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    annotation_type: str = Field(
        ...,
        pattern="^(user_note|ai_summary|ocr_output|llm_query|scene_description|action_detected|custom)$",
    )
    content: str
    metadata: Optional[dict[str, Any]] = None  # Confidence, model, tags, etc.
    created_by: str = "system"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        """Duration covered by this annotation."""
        return (self.end_timestamp - self.start_timestamp).total_seconds()


# Request/Response models for API
class CaptureVideoRequest(BaseModel):
    """Request to capture a video file."""

    filepath: str
    frame_interval: int = 5  # seconds
    chunk_duration: int = 300  # 5 minutes


class TimeRangeQuery(BaseModel):
    """Query parameters for time range."""

    start: datetime
    end: datetime
    source_id: Optional[int] = None


class FrameResponse(BaseModel):
    """Response containing frame data."""

    id: int
    source_id: int
    timestamp: datetime
    width: int
    height: int
    format: str
    size_bytes: int
    # Note: image_data not included in response by default (too large)


class TranscriptionResponse(BaseModel):
    """Response containing transcription data."""

    id: int
    source_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    text: str
    confidence: Optional[float]
    language: Optional[str]
    word_count: int
