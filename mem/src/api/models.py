"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# Request models


class CaptureRequest(BaseModel):
    """Request to capture a video file."""

    filepath: str = Field(..., description="Path to video file")
    config: Optional[dict[str, Any]] = Field(
        default=None, description="Optional capture configuration"
    )


# Stream models


class CreateStreamRequest(BaseModel):
    """Request to create a new stream session."""

    name: Optional[str] = Field(default=None, description="Optional stream name")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Optional metadata"
    )


class StreamSessionResponse(BaseModel):
    """Response containing stream session details."""

    session_id: str
    stream_key: str
    name: Optional[str] = None
    status: Literal["waiting", "live", "ended", "error"]
    source_id: Optional[int] = None
    rtmp_url: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    resolution: Optional[str] = None
    frames_received: int = 0
    frames_stored: int = 0
    duration: Optional[float] = None


class StreamListResponse(BaseModel):
    """Response containing list of stream sessions."""

    streams: list[StreamSessionResponse]
    active_count: int
    total_count: int


class StreamStatusResponse(BaseModel):
    """Response containing streaming server status."""

    server: dict[str, Any]
    streams: dict[str, Any]


class SearchRequest(BaseModel):
    """Generic search request parameters."""

    type: Literal["timeline", "frame", "transcript", "all"] = Field(
        ..., description="Search type"
    )
    start: Optional[datetime] = Field(
        default=None, description="Start time for timeline searches"
    )
    end: Optional[datetime] = Field(
        default=None, description="End time for timeline searches"
    )
    source_id: Optional[int] = Field(default=None, description="Filter by source ID")
    q: Optional[str] = Field(
        default=None, description="Query text for transcript search"
    )
    frame_id: Optional[int] = Field(
        default=None, description="Frame ID for direct frame access"
    )
    limit: Optional[int] = Field(default=100, description="Maximum results to return")
    offset: Optional[int] = Field(default=0, description="Pagination offset")
    format: Optional[str] = Field(
        default="jpeg", description="Output format for frames"
    )
    size: Optional[str] = Field(
        default=None, description="Size for frame output (e.g., '640x480', 'thumb')"
    )


# Response models


class CaptureResponse(BaseModel):
    """Response for capture request."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    message: Optional[str] = Field(default=None, description="Status message")


class FrameData(BaseModel):
    """Frame data in search results."""

    frame_id: int
    timestamp: datetime
    source_id: int
    perceptual_hash: str
    similarity_score: Optional[float] = None
    url: Optional[str] = Field(default=None, description="URL to retrieve frame image")
    metadata: Optional[dict[str, Any]] = None


class TranscriptData(BaseModel):
    """Transcript data in search results."""

    transcription_id: int
    timestamp: datetime
    source_id: int
    text: str
    confidence: Optional[float] = None
    language: Optional[str] = None
    start_timestamp: datetime
    end_timestamp: datetime
    # Speaker identification fields
    speaker_name: Optional[str] = None
    speaker_confidence: Optional[float] = None


class AnnotationData(BaseModel):
    """Annotation data for API responses."""

    annotation_id: int
    annotation_type: str
    content: str
    metadata: Optional[dict[str, Any]] = None
    created_by: str = "system"
    created_at: datetime


class TimelineEntry(BaseModel):
    """Single timeline entry with frame and transcript."""

    timestamp: datetime
    source_id: int
    source_type: Optional[str] = None
    source_filename: Optional[str] = None
    source_location: Optional[str] = None
    frame: Optional[FrameData] = None
    transcript: Optional[TranscriptData] = None
    scene_changed: bool = False
    annotations: list[AnnotationData] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Generic search response."""

    type: str = Field(..., description="Type of search performed")
    count: int = Field(..., description="Total number of results")
    results: list[Any] = Field(..., description="Search results")
    pagination: Optional[dict[str, Any]] = Field(
        default=None, description="Pagination info"
    )


class TimelineResponse(BaseModel):
    """Timeline search response."""

    type: Literal["timeline"] = "timeline"
    count: int
    entries: list[TimelineEntry]
    stats: Optional[dict[str, Any]] = None
    pagination: Optional[dict[str, Any]] = None


class TranscriptSearchResponse(BaseModel):
    """Transcript search response."""

    type: Literal["transcript"] = "transcript"
    count: int
    results: list[TranscriptData]
    pagination: Optional[dict[str, Any]] = None


class StatusResponse(BaseModel):
    """System status response."""

    system: dict[str, Any] = Field(..., description="System info")
    jobs: dict[str, Any] = Field(..., description="Job queue status")
    storage: dict[str, Any] = Field(..., description="Storage statistics")
    sources: dict[str, Any] = Field(..., description="Source statistics")


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(
        default=None, description="Detailed error information"
    )


# Annotation request/response models
class CreateAnnotationRequest(BaseModel):
    """Request to create a new annotation."""

    source_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    annotation_type: str = Field(
        ...,
        pattern="^(user_note|ai_summary|ocr_output|llm_query|scene_description|action_detected|custom)$",
    )
    content: str
    metadata: Optional[dict[str, Any]] = None
    created_by: Optional[str] = "system"


class UpdateAnnotationRequest(BaseModel):
    """Request to update an existing annotation."""

    content: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    annotation_type: Optional[str] = Field(
        default=None,
        pattern="^(user_note|ai_summary|ocr_output|llm_query|scene_description|action_detected|custom)$",
    )


class AnnotationResponse(BaseModel):
    """Response for annotation operations."""

    annotation_id: int
    source_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    annotation_type: str
    content: str
    metadata: Optional[dict[str, Any]] = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class BatchAnnotationRequest(BaseModel):
    """Request to create multiple annotations."""

    source_id: int
    annotations: list[CreateAnnotationRequest]


class AnnotationListResponse(BaseModel):
    """Response containing list of annotations."""

    annotations: list[AnnotationResponse]
    count: int
    pagination: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# Voice profile request/response models
class VoiceProfileResponse(BaseModel):
    """Response for voice profile operations."""

    profile_id: int
    name: str
    display_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Optional[dict[str, Any]] = None

    @classmethod
    def from_model(cls, profile: "SpeakerProfile") -> "VoiceProfileResponse":
        """Create response from SpeakerProfile model."""
        from src.storage.models import SpeakerProfile

        return cls(
            profile_id=profile.profile_id,
            name=profile.name,
            display_name=profile.display_name,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            metadata=profile.metadata,
        )


class VoiceProfileListResponse(BaseModel):
    """Response containing list of voice profiles."""

    profiles: list[VoiceProfileResponse]
    count: int


# Settings request/response models


class CaptureFrameSettingsResponse(BaseModel):
    """Capture frame settings."""

    interval_seconds: int
    jpeg_quality: int
    enable_deduplication: bool
    similarity_threshold: float


class CaptureAudioSettingsResponse(BaseModel):
    """Capture audio settings."""

    chunk_duration_seconds: int
    sample_rate: int


class CaptureSettingsResponse(BaseModel):
    """Combined capture settings."""

    frame: CaptureFrameSettingsResponse
    audio: CaptureAudioSettingsResponse


class STTDSettingsResponse(BaseModel):
    """STTD server settings."""

    host: str
    port: int
    timeout: float


class StreamingSettingsResponse(BaseModel):
    """Streaming settings."""

    frame_interval_seconds: int
    max_concurrent_streams: int


class SettingsResponse(BaseModel):
    """Full settings response."""

    capture: CaptureSettingsResponse
    sttd: STTDSettingsResponse
    streaming: StreamingSettingsResponse


class CaptureFrameSettingsUpdate(BaseModel):
    """Update capture frame settings."""

    interval_seconds: Optional[int] = None
    jpeg_quality: Optional[int] = None
    enable_deduplication: Optional[bool] = None
    similarity_threshold: Optional[float] = None


class CaptureAudioSettingsUpdate(BaseModel):
    """Update capture audio settings."""

    chunk_duration_seconds: Optional[int] = None
    sample_rate: Optional[int] = None


class CaptureSettingsUpdate(BaseModel):
    """Update capture settings."""

    frame: Optional[CaptureFrameSettingsUpdate] = None
    audio: Optional[CaptureAudioSettingsUpdate] = None


class STTDSettingsUpdate(BaseModel):
    """Update STTD server settings."""

    host: Optional[str] = None
    port: Optional[int] = None
    timeout: Optional[float] = None


class StreamingSettingsUpdate(BaseModel):
    """Update streaming settings."""

    frame_interval_seconds: Optional[int] = None
    max_concurrent_streams: Optional[int] = None


class UpdateSettingsRequest(BaseModel):
    """Request to update settings."""

    capture: Optional[CaptureSettingsUpdate] = None
    sttd: Optional[STTDSettingsUpdate] = None
    streaming: Optional[StreamingSettingsUpdate] = None


class UpdateSettingsResponse(BaseModel):
    """Response after updating settings."""

    settings: SettingsResponse
    restart_required: bool
    restart_reason: Optional[str] = None


class DefaultSettingsResponse(BaseModel):
    """Default settings values."""

    capture: CaptureSettingsResponse
    sttd: STTDSettingsResponse
    streaming: StreamingSettingsResponse
