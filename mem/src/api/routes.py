"""API route definitions."""

import logging
import re
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from src.api.models import (
    AnnotationData,
    AnnotationListResponse,
    AnnotationResponse,
    BatchAnnotationRequest,
    CaptureRequest,
    CaptureResponse,
    CreateAnnotationRequest,
    CreateStreamRequest,
    FrameData,
    SearchResponse,
    StatusResponse,
    StreamListResponse,
    StreamSessionResponse,
    StreamStatusResponse,
    TimelineEntry,
    TimelineResponse,
    TranscriptData,
    TranscriptSearchResponse,
    UpdateAnnotationRequest,
)
from src.api.services import (
    AnnotationService,
    CaptureService,
    SearchService,
    StreamingService,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
capture_service = CaptureService()
search_service = SearchService()
annotation_service = AnnotationService()
streaming_service = StreamingService()


@router.post("/capture", response_model=CaptureResponse)
async def capture_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload and process a video file for frame and transcript extraction.

    Args:
        file: Uploaded video file
        background_tasks: FastAPI background tasks

    Returns:
        Job ID and status
    """
    try:
        # Validate filename format (YYYY-MM-DD_HH-MM-SS.mkv)
        filename = file.filename

        # Check file extension
        if not filename.endswith(".mkv"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file extension. File must be .mkv format",
            )

        # Check filename format
        # Pattern: YYYY-MM-DD_HH-MM-SS.mkv
        pattern = r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.mkv$"
        if not re.match(pattern, filename):
            raise HTTPException(
                status_code=400,
                detail="Invalid filename format. Expected: YYYY-MM-DD_HH-MM-SS.mkv",
            )

        # Check file size (5GB max)
        max_size = 5 * 1024 * 1024 * 1024  # 5GB in bytes
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=413, detail="File size exceeds maximum allowed size of 5GB"
            )

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
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Capture request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search(
    type: str = Query(..., description="Search type: timeline, frame, transcript, all"),
    start: Optional[datetime] = Query(None, description="Start time for timeline search"),
    end: Optional[datetime] = Query(None, description="End time for timeline search"),
    source_id: Optional[int] = Query(None, description="Filter by source ID"),
    q: Optional[str] = Query(None, description="Query text for transcript search"),
    frame_id: Optional[int] = Query(None, description="Frame ID for direct access"),
    limit: int = Query(100, description="Maximum results to return"),
    offset: int = Query(0, description="Pagination offset"),
    format: str = Query("jpeg", description="Output format for frames"),
    size: Optional[str] = Query(None, description="Size for frame output"),
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
                raise HTTPException(status_code=400, detail="frame_id required for frame type")

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

            result = search_service.search_timeline(start, end, source_id, limit, offset)

            # Convert to proper response model
            entries = []
            for entry in result["entries"]:
                timeline_entry = TimelineEntry(
                    timestamp=entry["timestamp"],
                    source_id=entry["source_id"],
                    scene_changed=entry.get("scene_changed", False),
                )

                if "frame" in entry:
                    timeline_entry.frame = FrameData(**entry["frame"])

                if "transcript" in entry:
                    timeline_entry.transcript = TranscriptData(**entry["transcript"])

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
                raise HTTPException(
                    status_code=400,
                    detail="Query text 'q' required for transcript search",
                )

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

            timeline_result = search_service.search_timeline(start, end, source_id, limit, offset)

            # If there's a text query, also search transcripts
            transcript_results = []
            if q:
                transcript_result = search_service.search_transcripts(q, source_id, limit, offset)
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
            raise HTTPException(status_code=400, detail=f"Invalid search type: {type}")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=StatusResponse)
async def get_status():
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
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

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
        annotation_id = annotation_service.create_annotation(
            source_id=request.source_id,
            start_timestamp=request.start_timestamp,
            end_timestamp=request.end_timestamp,
            annotation_type=request.annotation_type,
            content=request.content,
            metadata=request.metadata,
            created_by=request.created_by or "system",
        )

        # Fetch and return the created annotation
        result = annotation_service.get_annotations(source_id=request.source_id, limit=1)
        if result["annotations"]:
            ann = result["annotations"][0]
            return AnnotationResponse(**ann)
        else:
            raise HTTPException(status_code=500, detail="Failed to retrieve created annotation")

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
            raise HTTPException(status_code=404, detail=f"Annotation {annotation_id} not found")

        # Fetch and return the updated annotation
        query = f"SELECT * FROM timeframe_annotations WHERE annotation_id = {annotation_id}"
        result = annotation_service.db.connection.execute(query).fetchone()
        if result:
            import json

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
        else:
            raise HTTPException(status_code=404, detail="Annotation not found after update")

    except HTTPException:
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
            raise HTTPException(status_code=404, detail=f"Annotation {annotation_id} not found")

        return {"message": f"Annotation {annotation_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete annotation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/annotations", response_model=AnnotationListResponse)
async def get_annotations(
    source_id: Optional[int] = Query(None, description="Filter by source ID"),
    start: Optional[datetime] = Query(None, description="Start timestamp"),
    end: Optional[datetime] = Query(None, description="End timestamp"),
    type: Optional[str] = Query(None, description="Filter by annotation type"),
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


# Stream endpoints
@router.post("/streams/create", response_model=StreamSessionResponse)
async def create_stream(request: CreateStreamRequest):
    """Create a new stream session for OBS Studio.

    Args:
        request: Stream creation request

    Returns:
        Stream session details including RTMP URL
    """
    try:
        session = streaming_service.create_stream(name=request.name, metadata=request.metadata)

        return StreamSessionResponse(
            session_id=session.session_id,
            stream_key=session.stream_key,
            name=session.stream_name,
            status=session.status,
            source_id=session.source_id,
            rtmp_url=streaming_service.get_rtmp_url(session.stream_key),
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
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Create stream failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streams", response_model=StreamListResponse)
async def list_streams():
    """List all stream sessions.

    Returns:
        List of all stream sessions with their status
    """
    try:
        sessions = streaming_service.get_all_sessions()
        active_count = sum(1 for s in sessions if s.status == "live")

        stream_responses = []
        for session in sessions:
            stream_responses.append(
                StreamSessionResponse(
                    session_id=session.session_id,
                    stream_key=session.stream_key,
                    name=session.stream_name,
                    status=session.status,
                    source_id=session.source_id,
                    rtmp_url=streaming_service.get_rtmp_url(session.stream_key),
                    started_at=session.started_at,
                    ended_at=session.ended_at,
                    resolution=(f"{session.width}x{session.height}" if session.width else None),
                    frames_received=session.frames_received,
                    frames_stored=session.frames_stored,
                    duration=(
                        (datetime.now() - session.started_at).total_seconds()
                        if session.started_at and session.status == "live"
                        else None
                    ),
                )
            )

        return StreamListResponse(
            streams=stream_responses,
            active_count=active_count,
            total_count=len(sessions),
        )
    except Exception as e:
        logger.error(f"List streams failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streams/{stream_key}", response_model=StreamSessionResponse)
async def get_stream(stream_key: str):
    """Get details for a specific stream session.

    Args:
        stream_key: Stream key identifier

    Returns:
        Stream session details
    """
    try:
        session = streaming_service.get_session(stream_key)
        if not session:
            raise HTTPException(status_code=404, detail=f"Stream {stream_key} not found")

        return StreamSessionResponse(
            session_id=session.session_id,
            stream_key=session.stream_key,
            name=session.stream_name,
            status=session.status,
            source_id=session.source_id,
            rtmp_url=streaming_service.get_rtmp_url(session.stream_key),
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get stream failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/streams/{stream_key}/start")
async def start_stream(stream_key: str):
    """Start receiving stream from OBS Studio.

    Args:
        stream_key: Stream key to start

    Returns:
        Success status
    """
    try:
        success = streaming_service.start_stream(stream_key)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to start stream")

        return {"message": f"Stream {stream_key} started successfully"}
    except Exception as e:
        logger.error(f"Start stream failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/streams/{stream_key}/stop")
async def stop_stream(stream_key: str):
    """Stop an active stream.

    Args:
        stream_key: Stream key to stop

    Returns:
        Success status
    """
    try:
        success = streaming_service.stop_stream(stream_key)
        if not success:
            raise HTTPException(status_code=404, detail=f"Stream {stream_key} not found")

        return {"message": f"Stream {stream_key} stopped successfully"}
    except Exception as e:
        logger.error(f"Stop stream failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/streams/{stream_key}")
async def delete_stream(stream_key: str):
    """Delete a stream session.

    Args:
        stream_key: Stream key to delete

    Returns:
        Success status
    """
    try:
        success = streaming_service.delete_session(stream_key)
        if not success:
            raise HTTPException(status_code=404, detail=f"Stream {stream_key} not found")

        return {"message": f"Stream {stream_key} deleted successfully"}
    except Exception as e:
        logger.error(f"Delete stream failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streams/status", response_model=StreamStatusResponse)
async def get_streaming_status():
    """Get overall streaming server status.

    Returns:
        Server and stream statistics
    """
    try:
        status = streaming_service.get_status()
        return StreamStatusResponse(server=status["server"], streams=status["streams"])
    except Exception as e:
        logger.error(f"Get streaming status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
