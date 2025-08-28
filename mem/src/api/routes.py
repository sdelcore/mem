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
    FrameData,
    SearchResponse,
    StatusResponse,
    TimelineEntry,
    TimelineResponse,
    TranscriptData,
    TranscriptSearchResponse,
    UpdateAnnotationRequest,
)
from src.api.services import AnnotationService, CaptureService, SearchService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
capture_service = CaptureService()
search_service = SearchService()
annotation_service = AnnotationService()


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
