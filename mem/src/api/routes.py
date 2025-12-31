"""API route definitions."""

import json
import logging
import re
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.exceptions import (
    ResourceNotFoundError,
    StreamError,
    ValidationError,
)
from src.api.models import (
    AnnotationData,
    AnnotationListResponse,
    AnnotationResponse,
    BatchAnnotationRequest,
    CaptureResponse,
    CreateAnnotationRequest,
    CreateStreamRequest,
    DefaultSettingsResponse,
    FrameData,
    SearchResponse,
    SettingsResponse,
    StatusResponse,
    StreamListResponse,
    StreamSessionResponse,
    StreamStatusResponse,
    TimelineEntry,
    TimelineResponse,
    TranscriptData,
    TranscriptSearchResponse,
    UpdateAnnotationRequest,
    UpdateSettingsRequest,
    UpdateSettingsResponse,
    VoiceProfileListResponse,
    VoiceProfileResponse,
)
from src.api.services import (
    AnnotationService,
    CaptureService,
    SearchService,
    get_rtmp_server,
)
from src.api.settings import SettingsService
from src.api.voice_profiles import get_voice_profile_service
from src.capture.stream_server import StreamSession

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize services
capture_service = CaptureService()
search_service = SearchService()
annotation_service = AnnotationService()
settings_service = SettingsService()


def _build_stream_response(session: StreamSession) -> StreamSessionResponse:
    """Build a StreamSessionResponse from a StreamSession."""
    rtmp_server = get_rtmp_server()
    return StreamSessionResponse(
        session_id=session.session_id,
        stream_key=session.stream_key,
        name=session.stream_name,
        status=session.status,
        source_id=session.source_id,
        rtmp_url=rtmp_server.get_stream_url(session.stream_key),
        started_at=session.started_at,
        ended_at=session.ended_at,
        resolution=f"{session.width}x{session.height}" if session.width else None,
        frames_received=session.frames_received,
        frames_stored=session.frames_stored,
        duration=(
            (datetime.now() - session.started_at).total_seconds()
            if session.started_at and session.status == "live"
            else None
        ),
    )


@router.post("/capture", response_model=CaptureResponse)
@limiter.limit("5/minute")
async def capture_video(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload and process a video file for frame and transcript extraction.

    Args:
        request: FastAPI request object (required for rate limiting)
        file: Uploaded video file
        background_tasks: FastAPI background tasks

    Returns:
        Job ID and status
    """
    try:
        filename = file.filename

        # Check filename format: YYYY-MM-DD_HH-MM-SS.(mp4|mkv)
        pattern = r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.(mp4|mkv)$"
        if not re.match(pattern, filename):
            raise ValidationError(
                "Invalid filename format. Expected: YYYY-MM-DD_HH-MM-SS.mp4 or .mkv"
            )

        # Check file size (5GB max)
        max_size = 5 * 1024 * 1024 * 1024  # 5GB in bytes
        content = await file.read()
        if len(content) > max_size:
            raise ValidationError("File size exceeds maximum allowed size of 5GB")

        # Reset file pointer after reading
        await file.seek(0)

        # Create uploads directory if it doesn't exist
        uploads_dir = Path("data/uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded file
        file_path = uploads_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved uploaded file to {file_path}")

        # Start capture job
        job_id = capture_service.start_capture(str(file_path), None)

        # Get job status
        job = capture_service.get_job_status(job_id)

        return CaptureResponse(
            job_id=job_id, status=job["status"], message=f"Processing video: {filename}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Capture request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
@limiter.limit("60/minute")
async def search(
    request: Request,
    type: str = Query(..., description="Search type: timeline, frame, transcript, all"),
    start: datetime | None = Query(
        None, description="Start time for timeline search"
    ),
    end: datetime | None = Query(None, description="End time for timeline search"),
    source_id: int | None = Query(None, description="Filter by source ID"),
    q: str | None = Query(None, description="Query text for transcript search"),
    frame_id: int | None = Query(None, description="Frame ID for direct access"),
    limit: int = Query(100, description="Maximum results to return"),
    offset: int = Query(0, description="Pagination offset"),
    format: str = Query("jpeg", description="Output format for frames"),
    size: str | None = Query(None, description="Size for frame output"),
):
    """Universal search endpoint for all data retrieval.

    Supports multiple search types:
    - timeline: Get frames and transcripts in time range
    - frame: Get specific frame image
    - transcript: Search transcripts by text
    - all: Combined search
    """
    try:
        # Handle frame retrieval
        if type == "frame":
            if not frame_id:
                raise ValidationError("frame_id required for frame type")

            # Get frame image data
            image_bytes, content_type = search_service.get_frame(frame_id, format, size)

            # Return as image response
            return StreamingResponse(
                BytesIO(image_bytes),
                media_type=content_type,
                headers={
                    "Content-Disposition": f"inline; filename=frame_{frame_id}.{format}",
                    "Cache-Control": "public, max-age=3600",
                },
            )

        # Handle timeline search
        elif type == "timeline":
            # Default to last 24 hours if not specified
            if not end:
                end = datetime.now()
            if not start:
                start = end - timedelta(days=1)

            result = search_service.search_timeline(
                start, end, source_id, limit, offset
            )

            # Convert to proper response model
            entries = []
            for entry in result["entries"]:
                timeline_entry = TimelineEntry(
                    timestamp=entry["timestamp"],
                    source_id=entry["source_id"],
                    source_type=entry.get("source_type"),
                    source_filename=entry.get("source_filename"),
                    source_location=entry.get("source_location"),
                    scene_changed=entry.get("scene_changed", False),
                )

                if "frame" in entry and entry["frame"]:
                    timeline_entry.frame = FrameData(**entry["frame"])

                if "transcript" in entry and entry["transcript"]:
                    timeline_entry.transcript = TranscriptData(**entry["transcript"])

                # Add annotations
                for ann in entry.get("annotations", []):
                    timeline_entry.annotations.append(AnnotationData(**ann))

                entries.append(timeline_entry)

            return TimelineResponse(
                type="timeline",
                count=result["count"],
                entries=entries,
                pagination=result.get("pagination"),
            )

        # Handle transcript search
        elif type == "transcript":
            if not q:
                raise ValidationError("Query text 'q' required for transcript search")

            result = search_service.search_transcripts(q, source_id, limit, offset)

            return TranscriptSearchResponse(
                type="transcript",
                count=result["count"],
                results=[TranscriptData(**t) for t in result["results"]],
                pagination=result.get("pagination"),
            )

        # Handle combined search
        elif type == "all":
            # This would combine timeline and transcript searches
            # For now, just do a timeline search
            if not end:
                end = datetime.now()
            if not start:
                start = end - timedelta(days=1)

            timeline_result = search_service.search_timeline(
                start, end, source_id, limit, offset
            )

            # If there's a text query, also search transcripts
            transcript_results = []
            if q:
                transcript_result = search_service.search_transcripts(
                    q, source_id, limit, offset
                )
                transcript_results = transcript_result["results"]

            return SearchResponse(
                type="all",
                count=timeline_result["count"] + len(transcript_results),
                results={
                    "timeline": timeline_result["entries"],
                    "transcripts": transcript_results,
                },
                pagination=timeline_result.get("pagination"),
            )

        else:
            raise ValidationError(f"Invalid search type: {type}")

    except ValueError as e:
        raise ResourceNotFoundError("Resource", str(e))
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=StatusResponse)
@limiter.limit("100/minute")
async def get_status(request: Request):
    """Get system status and statistics.

    Returns:
        System status including jobs, storage, and source statistics
    """
    try:
        status = search_service.get_status()
        return StatusResponse(**status)

    except Exception as e:
        logger.error(f"Status request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific capture job.

    Args:
        job_id: Job identifier

    Returns:
        Job status and details
    """
    job = capture_service.get_job_status(job_id)
    if not job:
        raise ResourceNotFoundError("Job", job_id)

    return job


# Annotation endpoints
@router.post("/annotations", response_model=AnnotationResponse)
async def create_annotation(request: CreateAnnotationRequest):
    """Create a new annotation for a timeframe.

    Args:
        request: Annotation details

    Returns:
        Created annotation
    """
    try:
        _ = annotation_service.create_annotation(
            source_id=request.source_id,
            start_timestamp=request.start_timestamp,
            end_timestamp=request.end_timestamp,
            annotation_type=request.annotation_type,
            content=request.content,
            metadata=request.metadata,
            created_by=request.created_by or "system",
        )

        # Fetch and return the created annotation
        result = annotation_service.get_annotations(
            source_id=request.source_id, limit=1
        )
        if result["annotations"]:
            ann = result["annotations"][0]
            return AnnotationResponse(**ann)
        else:
            raise ResourceNotFoundError("Annotation", "created annotation")

    except Exception as e:
        logger.error(f"Create annotation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/annotations/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(annotation_id: int, request: UpdateAnnotationRequest):
    """Update an existing annotation.

    Args:
        annotation_id: ID of annotation to update
        request: Fields to update

    Returns:
        Updated annotation
    """
    try:
        updates = {}
        if request.content is not None:
            updates["content"] = request.content
        if request.metadata is not None:
            updates["metadata"] = request.metadata
        if request.annotation_type is not None:
            updates["annotation_type"] = request.annotation_type

        success = annotation_service.update_annotation(annotation_id, updates)
        if not success:
            raise ResourceNotFoundError("Annotation", annotation_id)

        # Fetch and return the updated annotation
        result = annotation_service.db.connection.execute(
            "SELECT * FROM timeframe_annotations WHERE annotation_id = ?",
            [annotation_id]
        ).fetchone()
        if not result:
            raise ResourceNotFoundError("Annotation", annotation_id)

        return AnnotationResponse(
            annotation_id=result[0],
            source_id=result[1],
            start_timestamp=result[2],
            end_timestamp=result[3],
            annotation_type=result[4],
            content=result[5],
            metadata=json.loads(result[6]) if result[6] else None,
            created_by=result[7],
            created_at=result[8],
            updated_at=result[9],
        )

    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Update annotation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(annotation_id: int):
    """Delete an annotation.

    Args:
        annotation_id: ID of annotation to delete

    Returns:
        Success message
    """
    try:
        success = annotation_service.delete_annotation(annotation_id)
        if not success:
            raise ResourceNotFoundError("Annotation", annotation_id)

        return {"message": f"Annotation {annotation_id} deleted successfully"}

    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Delete annotation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/annotations", response_model=AnnotationListResponse)
async def get_annotations(
    source_id: int | None = Query(None, description="Filter by source ID"),
    start: datetime | None = Query(None, description="Start timestamp"),
    end: datetime | None = Query(None, description="End timestamp"),
    type: str | None = Query(None, description="Filter by annotation type"),
    limit: int = Query(100, description="Maximum results"),
    offset: int = Query(0, description="Pagination offset"),
):
    """Get annotations with filters.

    Args:
        source_id: Optional source filter
        start: Optional start time filter
        end: Optional end time filter
        type: Optional annotation type filter
        limit: Maximum results
        offset: Pagination offset

    Returns:
        List of annotations
    """
    try:
        result = annotation_service.get_annotations(
            source_id=source_id,
            start=start,
            end=end,
            annotation_type=type,
            limit=limit,
            offset=offset,
        )

        annotations = []
        for ann in result["annotations"]:
            annotations.append(AnnotationResponse(**ann))

        return AnnotationListResponse(
            annotations=annotations,
            count=result["count"],
            pagination=result["pagination"],
        )

    except Exception as e:
        logger.error(f"Get annotations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/annotations/batch")
async def batch_create_annotations(request: BatchAnnotationRequest):
    """Create multiple annotations in batch.

    Args:
        request: Batch annotation request

    Returns:
        List of created annotation IDs
    """
    try:
        annotations_data = []
        for ann in request.annotations:
            annotations_data.append(
                {
                    "start_timestamp": ann.start_timestamp,
                    "end_timestamp": ann.end_timestamp,
                    "annotation_type": ann.annotation_type,
                    "content": ann.content,
                    "metadata": ann.metadata,
                    "created_by": ann.created_by or "system",
                }
            )

        annotation_ids = annotation_service.batch_create_annotations(
            request.source_id, annotations_data
        )

        return {
            "annotation_ids": annotation_ids,
            "count": len(annotation_ids),
            "message": f"Created {len(annotation_ids)} annotations",
        }

    except Exception as e:
        logger.error(f"Batch create annotations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/annotations/quick")
async def create_quick_annotation(
    timestamp: datetime = Query(..., description="Timestamp for the annotation"),
    content: str = Query(..., description="Annotation content"),
    annotation_type: str = Query("user_note", description="Annotation type"),
):
    """Create an annotation without specifying source_id.

    Auto-assigns to a user_annotations source. Useful for quick notes
    from the UI without needing to know the source_id.

    Args:
        timestamp: When the annotation applies
        content: The annotation text content
        annotation_type: Type of annotation (default: user_note)

    Returns:
        Created annotation details
    """
    try:
        source_id = annotation_service.get_or_create_user_annotations_source()

        annotation_id = annotation_service.create_annotation(
            source_id=source_id,
            start_timestamp=timestamp,
            end_timestamp=timestamp,
            annotation_type=annotation_type,
            content=content,
            created_by="user",
        )

        return {
            "status": "success",
            "annotation_id": annotation_id,
            "source_id": source_id,
            "timestamp": timestamp.isoformat(),
            "content": content,
            "annotation_type": annotation_type,
        }

    except Exception as e:
        logger.error(f"Quick create annotation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Stream endpoints
@router.post("/streams/create", response_model=StreamSessionResponse)
@limiter.limit("10/minute")
async def create_stream(request: Request, request_body: CreateStreamRequest):
    """Create a new stream session for OBS Studio."""
    try:
        rtmp_server = get_rtmp_server()
        session = rtmp_server.create_session(stream_name=request_body.name)
        return _build_stream_response(session)
    except RuntimeError as e:
        raise StreamError(str(e))
    except Exception as e:
        logger.error(f"Create stream failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streams", response_model=StreamListResponse)
@limiter.limit("100/minute")
async def list_streams(request: Request):
    """List all stream sessions."""
    try:
        rtmp_server = get_rtmp_server()
        sessions = rtmp_server.get_all_sessions()
        active_count = sum(1 for s in sessions if s.status == "live")
        return StreamListResponse(
            streams=[_build_stream_response(s) for s in sessions],
            active_count=active_count,
            total_count=len(sessions),
        )
    except Exception as e:
        logger.error(f"List streams failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streams/{stream_key}", response_model=StreamSessionResponse)
async def get_stream(stream_key: str):
    """Get details for a specific stream session."""
    rtmp_server = get_rtmp_server()
    session = rtmp_server.get_session(stream_key)
    if not session:
        raise ResourceNotFoundError("Stream", stream_key)
    return _build_stream_response(session)


@router.post("/streams/{stream_key}/stop")
async def stop_stream(stream_key: str):
    """Stop an active stream."""
    rtmp_server = get_rtmp_server()
    if not rtmp_server.stop_stream(stream_key):
        raise ResourceNotFoundError("Stream", stream_key)
    return {"message": f"Stream {stream_key} stopped successfully"}


@router.delete("/streams/{stream_key}")
async def delete_stream(stream_key: str):
    """Delete a stream session."""
    rtmp_server = get_rtmp_server()
    if not rtmp_server.delete_session(stream_key):
        raise ResourceNotFoundError("Stream", stream_key)
    return {"message": f"Stream {stream_key} deleted successfully"}


@router.get("/streams/status", response_model=StreamStatusResponse)
async def get_streaming_status():
    """Get overall streaming server status."""
    rtmp_server = get_rtmp_server()
    status = rtmp_server.get_status()
    return StreamStatusResponse(server=status["server"], streams=status["streams"])


# ============================================================================
# RTMP Callback Endpoints (called by nginx-rtmp)
# ============================================================================


@router.post("/streams/rtmp-callback/publish")
async def rtmp_publish_callback(
    call: str = Form(...),
    app: str = Form(...),
    name: str = Form(...),  # This is the stream_key
    addr: str = Form(default=""),
    flashver: str = Form(default=""),
    swfurl: str = Form(default=""),
    tcurl: str = Form(default=""),
    pageurl: str = Form(default=""),
):
    """Nginx-rtmp on_publish callback when OBS starts streaming.

    Returns 2xx to allow publishing, anything else rejects the stream.
    This is called by nginx-rtmp when a client (OBS) connects and starts publishing.
    """
    logger.info(f"RTMP publish callback: app={app}, name={name}, addr={addr}")

    rtmp_server = get_rtmp_server()
    if rtmp_server.on_publish(name, addr):
        return Response(status_code=200, content="OK")

    # Return 403 to reject - causes OBS "could not access stream key" error
    logger.warning(f"Rejecting stream key {name} from {addr}")
    raise HTTPException(status_code=403, detail="Invalid or inactive stream key")


@router.post("/streams/rtmp-callback/publish-done")
async def rtmp_publish_done_callback(
    call: str = Form(...),
    app: str = Form(...),
    name: str = Form(...),
    addr: str = Form(default=""),
):
    """Nginx-rtmp on_publish_done callback when OBS stops streaming."""
    logger.info(f"RTMP publish-done callback: app={app}, name={name}")

    rtmp_server = get_rtmp_server()
    rtmp_server.on_publish_done(name)
    return Response(status_code=200, content="OK")


@router.post("/streams/rtmp-callback/play")
async def rtmp_play_callback(
    call: str = Form(default=""),
    app: str = Form(default=""),
    name: str = Form(default=""),
    addr: str = Form(default=""),
):
    """Nginx-rtmp on_play callback. Allow all playback for now."""
    logger.debug(f"RTMP play callback: app={app}, name={name}, addr={addr}")
    return Response(status_code=200, content="OK")


@router.post("/streams/rtmp-callback/play-done")
async def rtmp_play_done_callback(
    call: str = Form(default=""),
    app: str = Form(default=""),
    name: str = Form(default=""),
    addr: str = Form(default=""),
):
    """Nginx-rtmp on_play_done callback."""
    logger.debug(f"RTMP play-done callback: app={app}, name={name}")
    return Response(status_code=200, content="OK")


# ============================================================================
# Frame Ingestion Endpoint (called by nginx exec_push via stream_handler.py)
# ============================================================================


@router.post("/streams/{stream_key}/frame")
async def ingest_stream_frame(
    stream_key: str,
    file: UploadFile = File(...),
):
    """Receive a frame from nginx exec_push.

    This endpoint is called by the stream_handler.py script running in the
    nginx-rtmp container. It extracts frames from the RTMP stream using FFmpeg
    and POSTs them here for processing.
    """
    rtmp_server = get_rtmp_server()

    frame_data = await file.read()
    if not frame_data:
        logger.warning(f"Empty frame received for stream {stream_key}")
        raise HTTPException(status_code=400, detail="Empty frame data")

    if rtmp_server.ingest_frame(stream_key, frame_data):
        return {"status": "ok"}

    logger.warning(f"Failed to ingest frame for stream {stream_key}")
    raise HTTPException(status_code=400, detail="Failed to ingest frame")


# Voice profile endpoints
@router.get("/voice-profiles", response_model=VoiceProfileListResponse)
async def list_voice_profiles():
    """List all registered voice profiles."""
    try:
        service = get_voice_profile_service()
        profiles = service.list_profiles()
        return VoiceProfileListResponse(
            profiles=[VoiceProfileResponse.from_model(p) for p in profiles],
            count=len(profiles),
        )
    except Exception as e:
        logger.error(f"Failed to list voice profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice-profiles/{profile_id}", response_model=VoiceProfileResponse)
async def get_voice_profile(profile_id: int):
    """Get a specific voice profile by ID."""
    try:
        service = get_voice_profile_service()
        profile = service.get_profile(profile_id)
        if not profile:
            raise ResourceNotFoundError("Voice profile", profile_id)
        return VoiceProfileResponse.from_model(profile)
    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to get voice profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice-profiles", response_model=VoiceProfileResponse)
async def create_voice_profile(
    name: str = Form(..., description="Unique identifier for the profile"),
    display_name: str | None = Form(None, description="Human-readable name"),
    file: UploadFile = File(..., description="Audio file for voice registration"),
):
    """Create a new voice profile from audio file upload.

    Supported audio formats: wav, mp3, m4a, webm, ogg
    Recommended audio length: 5-30 seconds of clear speech
    """
    try:
        # Validate file type
        allowed_extensions = {".wav", ".mp3", ".m4a", ".webm", ".ogg"}
        file_ext = Path(file.filename).suffix.lower() if file.filename else ""
        if file_ext not in allowed_extensions:
            raise ValidationError(
                f"Invalid file type. Supported: {', '.join(allowed_extensions)}"
            )

        # Read audio data
        audio_data = await file.read()

        # Validate minimum file size (roughly 1 second of audio)
        if len(audio_data) < 10000:  # ~10KB minimum
            raise ValidationError(
                "Audio file too short. Please provide at least 5 seconds of speech."
            )

        # Create profile
        service = get_voice_profile_service()
        profile = service.register_from_file(
            name=name,
            audio_data=audio_data,
            display_name=display_name,
            metadata={"original_filename": file.filename},
        )
        return VoiceProfileResponse.from_model(profile)

    except ValueError as e:
        raise ValidationError(str(e))
    except (ValidationError, ResourceNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Failed to create voice profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/voice-profiles/{profile_id}")
async def delete_voice_profile(profile_id: int):
    """Delete a voice profile."""
    try:
        service = get_voice_profile_service()
        if not service.delete_profile(profile_id):
            raise ResourceNotFoundError("Voice profile", profile_id)
        return {"message": f"Profile {profile_id} deleted successfully"}
    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to delete voice profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Transcription Speaker Editing
# ============================================================================


@router.patch("/transcriptions/{transcription_id}/speaker")
async def update_transcription_speaker(
    transcription_id: int,
    speaker_name: str = Body(..., embed=True),
    speaker_id: int | None = Body(None, embed=True),
):
    """Update the speaker label for a transcription.

    Allows manual override of speaker identification for a single transcription.
    Can use either free-text entry or select from registered voice profiles.

    Args:
        transcription_id: ID of transcription to update
        speaker_name: New speaker name (free text or from profile)
        speaker_id: Optional voice profile ID (if selecting from registered profiles)

    Returns:
        Updated speaker information
    """
    from src.config import config
    from src.storage.db import Database

    try:
        db = Database(db_path=config.database.path)
        db.connect()

        try:
            # Verify transcription exists
            result = db.connection.execute(
                "SELECT 1 FROM transcriptions WHERE transcription_id = ?",
                [transcription_id],
            ).fetchone()

            if not result:
                raise ResourceNotFoundError("Transcription", transcription_id)

            # Validate speaker_id if provided
            if speaker_id is not None:
                profile = db.get_speaker_profile(speaker_id)
                if not profile:
                    raise ResourceNotFoundError("Voice profile", speaker_id)

            # Update the transcription
            success = db.update_transcription_speaker(
                transcription_id=transcription_id,
                speaker_name=speaker_name,
                speaker_id=speaker_id,
                speaker_confidence=1.0,  # Manual override = 100% confidence
            )

            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update transcription speaker",
                )

            return {
                "transcription_id": transcription_id,
                "speaker_name": speaker_name,
                "speaker_id": speaker_id,
                "speaker_confidence": 1.0,
                "message": "Speaker updated successfully",
            }

        finally:
            db.disconnect()

    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to update transcription speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Voice Notes Endpoints
# ============================================================================


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
):
    """Transcribe audio file without saving to database.

    Returns transcription text only. Used for voice-to-text input
    in the annotation modal.

    Supported audio formats: wav, mp3, m4a, webm, ogg
    """
    import tempfile

    from src.api.services import UserRecordingService

    try:
        # Validate file type
        allowed_extensions = {".wav", ".mp3", ".m4a", ".webm", ".ogg"}
        file_ext = Path(file.filename).suffix.lower() if file.filename else ".webm"
        if file_ext not in allowed_extensions:
            raise ValidationError(
                f"Invalid file type. Supported: {', '.join(allowed_extensions)}"
            )

        # Read audio data
        audio_data = await file.read()

        # Validate minimum file size
        if len(audio_data) < 1000:  # ~1KB minimum
            raise ValidationError("Audio file too short.")

        # Save to temp file for transcription
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = Path(temp_file.name)

        try:
            # Transcribe without saving
            service = UserRecordingService()
            result = service.transcribe_audio_only(temp_path)

            return {
                "status": "success",
                "text": result["text"],
                "language": result["language"],
                "duration": result["duration"],
            }

        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

    except (ValidationError, ResourceNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Failed to transcribe audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice-notes")
async def create_voice_note(
    file: UploadFile = File(..., description="Audio file to transcribe"),
):
    """Create a transcription from audio file upload.

    The audio will be transcribed using STTD and speaker identification
    will be attempted using registered voice profiles. The result is stored
    as a transcription (not an annotation).

    Supported audio formats: wav, mp3, m4a, webm, ogg
    """
    import tempfile

    from src.api.services import UserRecordingService

    try:
        # Validate file type
        allowed_extensions = {".wav", ".mp3", ".m4a", ".webm", ".ogg"}
        file_ext = Path(file.filename).suffix.lower() if file.filename else ".webm"
        if file_ext not in allowed_extensions:
            raise ValidationError(
                f"Invalid file type. Supported: {', '.join(allowed_extensions)}"
            )

        # Read audio data
        audio_data = await file.read()

        # Validate minimum file size
        if len(audio_data) < 1000:  # ~1KB minimum
            raise ValidationError("Audio file too short.")

        # Save to temp file for transcription
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = Path(temp_file.name)

        try:
            # Create user recording transcription
            service = UserRecordingService()
            result = service.create_user_recording(temp_path)

            return {
                "status": "success",
                "transcription_id": result["transcription_id"],
                "transcription": result["transcription"],
                "speaker": result["speaker"],
                "timestamp": result["timestamp"],
                "duration": result.get("duration"),
                "metadata": result["metadata"],
            }

        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

    except (ValidationError, ResourceNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Failed to create voice note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Settings Endpoints
# ============================================================================


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current application settings.

    Returns all configurable settings for capture, transcription, and streaming.
    """
    try:
        return settings_service.get_settings()
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings", response_model=UpdateSettingsResponse)
async def update_settings(request: UpdateSettingsRequest):
    """Update application settings.

    Updates settings and persists them to config.yaml.
    Returns updated settings and indicates if restart is required.

    Note: Some settings (like transcription model, device) require a restart
    to take effect. The response will indicate which settings require restart.
    """
    try:
        return settings_service.update_settings(request)
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/defaults", response_model=DefaultSettingsResponse)
async def get_default_settings():
    """Get default settings values.

    Returns the default values for all settings, which can be used
    to reset settings to their original state.
    """
    try:
        return settings_service.get_defaults()
    except Exception as e:
        logger.error(f"Failed to get default settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
