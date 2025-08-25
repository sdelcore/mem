"""Pydantic models for database entities."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class Source(BaseModel):
    """Represents a video/stream source."""

    id: Optional[int] = None
    type: str = Field(..., pattern="^(video|stream|upload)$")
    filename: str
    start_timestamp: datetime
    end_timestamp: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    frame_count: int = 0
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class Frame(BaseModel):
    """Represents an extracted video frame."""

    id: Optional[int] = None
    source_id: int
    timestamp: datetime
    image_data: bytes  # BLOB data
    width: int
    height: int
    format: str = "jpeg"
    size_bytes: Optional[int] = None
    created_at: Optional[datetime] = None


class Transcription(BaseModel):
    """Represents an audio transcription."""

    id: Optional[int] = None
    source_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    text: str
    confidence: Optional[float] = None
    language: Optional[str] = None
    word_count: Optional[int] = None
    created_at: Optional[datetime] = None


class FrameAnalysis(BaseModel):
    """Represents analysis results for a frame."""

    id: Optional[int] = None
    frame_id: int
    model_name: str
    analysis_type: str
    result: Dict[str, Any]
    processing_time_ms: Optional[int] = None
    created_at: Optional[datetime] = None


class TranscriptAnalysis(BaseModel):
    """Represents analysis results for a transcript."""

    id: Optional[int] = None
    transcription_id: int
    model_name: str
    analysis_type: str
    result: Dict[str, Any]
    processing_time_ms: Optional[int] = None
    created_at: Optional[datetime] = None


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
