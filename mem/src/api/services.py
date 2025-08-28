"""Business logic services for API endpoints."""

import json
import logging
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from src.capture.pipeline import CaptureConfig, VideoCaptureProcessor
from src.config import config
from src.storage.db import Database

logger = logging.getLogger(__name__)

# In-memory job tracking (simple for now)
JOBS: dict[str, dict[str, Any]] = {}


class CaptureService:
    """Service for handling video capture operations."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.path

    def start_capture(self, filepath: str, capture_config: Optional[dict[str, Any]] = None) -> str:
        """Start video capture processing.

        Args:
            filepath: Path to video file
            capture_config: Optional capture configuration

        Returns:
            Job ID for tracking
        """
        job_id = str(uuid.uuid4())

        # Store job info
        JOBS[job_id] = {
            "id": job_id,
            "status": "queued",
            "filepath": filepath,
            "created_at": datetime.now(),
            "result": None,
            "error": None,
        }

        # In a real implementation, this would be queued to a background task
        # For now, we'll process synchronously but update job status
        try:
            JOBS[job_id]["status"] = "processing"

            # Create capture config
            cfg = CaptureConfig()
            if capture_config:
                if "frame_interval" in capture_config:
                    cfg.frame_interval = capture_config["frame_interval"]
                if "chunk_duration" in capture_config:
                    cfg.chunk_duration = capture_config["chunk_duration"]

            # Process video
            processor = VideoCaptureProcessor(db_path=self.db_path, config=cfg)
            result = processor.process_video(Path(filepath))

            # Update job with result
            JOBS[job_id]["status"] = "completed" if result["status"] == "success" else "failed"
            JOBS[job_id]["result"] = result
            JOBS[job_id]["completed_at"] = datetime.now()

        except Exception as e:
            logger.error(f"Capture job {job_id} failed: {e}")
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(e)
            JOBS[job_id]["completed_at"] = datetime.now()

        return job_id

    def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """Get status of a capture job.

        Args:
            job_id: Job identifier

        Returns:
            Job status dict or None if not found
        """
        return JOBS.get(job_id)


class SearchService:
    """Service for handling search and data retrieval operations."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.path
        self.db = Database(db_path=self.db_path)
        self.db.connect()

    def search_timeline(
        self,
        start: datetime,
        end: datetime,
        source_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search timeline entries within a time range.

        Args:
            start: Start time (local)
            end: End time (local)
            source_id: Optional source filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Timeline entries with metadata
        """
        # Get timeline entries from database
        query = """
        SELECT
            t.entry_id,
            t.source_id,
            t.timestamp,
            t.frame_id,
            t.transcription_id,
            t.similarity_score,
            f.perceptual_hash,
            f.metadata as frame_metadata,
            tr.text as transcript_text,
            tr.confidence,
            tr.language,
            tr.start_timestamp,
            tr.end_timestamp
        FROM timeline t
        LEFT JOIN frames f ON t.frame_id = f.frame_id
        LEFT JOIN transcriptions tr ON t.transcription_id = tr.transcription_id
        WHERE t.timestamp >= ? AND t.timestamp <= ?
        """

        params = [start, end]
        if source_id:
            query += " AND t.source_id = ?"
            params.append(source_id)

        query += f" ORDER BY t.timestamp LIMIT {limit} OFFSET {offset}"

        results = self.db.connection.execute(query, params).fetchall()

        # Get annotations for this timeframe
        annotations_by_timestamp = {}
        if results:
            # Get all source IDs in results
            source_ids = set(row[1] for row in results)
            for sid in source_ids:
                annotations = self.db.get_annotations_for_timeline(sid, start, end)
                for timestamp, anns in annotations.items():
                    if timestamp not in annotations_by_timestamp:
                        annotations_by_timestamp[timestamp] = []
                    annotations_by_timestamp[timestamp].extend(anns)

        entries = []
        for row in results:
            timestamp = row[2]
            entry = {
                "timestamp": timestamp,
                "source_id": row[1],
                "scene_changed": row[5] < 95.0 if row[5] else False,
                "annotations": [],  # Always include annotations array
            }

            # Add annotations for this timestamp
            if timestamp in annotations_by_timestamp:
                for ann in annotations_by_timestamp[timestamp]:
                    entry["annotations"].append(
                        {
                            "annotation_id": ann.annotation_id,
                            "annotation_type": ann.annotation_type,
                            "content": ann.content,
                            "metadata": ann.metadata,
                            "created_by": ann.created_by,
                            "created_at": ann.created_at,
                        }
                    )

            if row[3]:  # frame_id exists
                entry["frame"] = {
                    "frame_id": row[3],
                    "timestamp": row[2],
                    "source_id": row[1],
                    "perceptual_hash": row[6],
                    "similarity_score": row[5],
                    "url": f"/api/search?type=frame&frame_id={row[3]}",
                    "metadata": json.loads(row[7]) if row[7] else {},
                }

            if row[4]:  # transcription_id exists
                entry["transcript"] = {
                    "transcription_id": row[4],
                    "timestamp": row[2],
                    "source_id": row[1],
                    "text": row[8],
                    "confidence": row[9],
                    "language": row[10],
                    "start_timestamp": row[11],
                    "end_timestamp": row[12],
                }

            entries.append(entry)

        # Get total count
        count_query = """
        SELECT COUNT(*) FROM timeline t
        WHERE t.timestamp >= ? AND t.timestamp <= ?
        """
        count_params = [start, end]
        if source_id:
            count_query += " AND t.source_id = ?"
            count_params.append(source_id)

        total_count = self.db.connection.execute(count_query, count_params).fetchone()[0]

        return {
            "type": "timeline",
            "count": total_count,
            "entries": entries,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
            },
        }

    def get_frame(
        self, frame_id: int, format: str = "jpeg", size: Optional[str] = None
    ) -> tuple[bytes, str]:
        """Get frame image data.

        Args:
            frame_id: Frame identifier
            format: Output format (jpeg, png)
            size: Optional size (e.g., '640x480', 'thumb')

        Returns:
            Tuple of (image_bytes, content_type)
        """
        frame = self.db.get_frame(frame_id)
        if not frame:
            raise ValueError(f"Frame {frame_id} not found")

        # Load image from bytes
        img = Image.open(BytesIO(frame.image_data))

        # Resize if requested
        if size:
            if size == "thumb":
                img.thumbnail((320, 240), Image.Resampling.LANCZOS)
            elif "x" in size:
                width, height = map(int, size.split("x"))
                img = img.resize((width, height), Image.Resampling.LANCZOS)

        # Convert to requested format
        output = BytesIO()
        if format == "png":
            img.save(output, format="PNG")
            content_type = "image/png"
        else:  # Default to JPEG
            img.save(output, format="JPEG", quality=85)
            content_type = "image/jpeg"

        return output.getvalue(), content_type

    def search_transcripts(
        self,
        query: str,
        source_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search transcripts by text.

        Args:
            query: Search query text
            source_id: Optional source filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Matching transcripts
        """
        # Simple text search using LIKE
        search_query = """
        SELECT
            transcription_id,
            source_id,
            start_timestamp,
            end_timestamp,
            text,
            confidence,
            language
        FROM transcriptions
        WHERE LOWER(text) LIKE LOWER(?)
        """

        params = [f"%{query}%"]
        if source_id:
            search_query += " AND source_id = ?"
            params.append(source_id)

        search_query += f" ORDER BY start_timestamp DESC LIMIT {limit} OFFSET {offset}"

        results = self.db.connection.execute(search_query, params).fetchall()

        transcripts = []
        for row in results:
            transcripts.append(
                {
                    "transcription_id": row[0],
                    "source_id": row[1],
                    "timestamp": row[2],  # Use start_timestamp as primary timestamp
                    "start_timestamp": row[2],
                    "end_timestamp": row[3],
                    "text": row[4],
                    "confidence": row[5],
                    "language": row[6],
                }
            )

        # Get total count
        count_query = """
        SELECT COUNT(*) FROM transcriptions
        WHERE LOWER(text) LIKE LOWER(?)
        """
        count_params = [f"%{query}%"]
        if source_id:
            count_query += " AND source_id = ?"
            count_params.append(source_id)

        total_count = self.db.connection.execute(count_query, count_params).fetchone()[0]

        return {
            "type": "transcript",
            "count": total_count,
            "results": transcripts,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
            },
        }

    def get_status(self) -> dict[str, Any]:
        """Get system status and statistics.

        Returns:
            System status information
        """
        stats = self.db.get_statistics()

        # Count active/completed jobs
        active_jobs = sum(1 for j in JOBS.values() if j["status"] in ["queued", "processing"])
        completed_jobs = sum(1 for j in JOBS.values() if j["status"] == "completed")
        failed_jobs = sum(1 for j in JOBS.values() if j["status"] == "failed")

        return {
            "system": {
                "version": "1.0.0",
                "database": "connected",
                "uptime": None,  # Would need to track app start time
            },
            "jobs": {
                "active": active_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs,
                "total": len(JOBS),
            },
            "storage": {
                "frames_stored": stats["frames"]["unique"],
                "total_references": stats["frames"]["total_references"],
                "deduplication_rate": stats["frames"].get("deduplication_percentage", 0),
                "size_mb": stats["frames"].get("size_mb", 0),
            },
            "sources": {
                "total": stats["sources"]["total"],
                "total_hours": stats["sources"].get("total_hours", 0),
            },
        }

    def __del__(self):
        """Cleanup database connection."""
        if hasattr(self, "db"):
            self.db.disconnect()


class AnnotationService:
    """Service for handling annotation operations."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.path
        self.db = Database(db_path=self.db_path)
        self.db.connect()

    def create_annotation(
        self,
        source_id: int,
        start_timestamp: datetime,
        end_timestamp: datetime,
        annotation_type: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        created_by: str = "system",
    ) -> int:
        """Create a new annotation."""
        from src.storage.models import TimeframeAnnotation

        annotation = TimeframeAnnotation(
            source_id=source_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            annotation_type=annotation_type,
            content=content,
            metadata=metadata,
            created_by=created_by,
        )
        return self.db.create_annotation(annotation)

    def update_annotation(self, annotation_id: int, updates: dict[str, Any]) -> bool:
        """Update an existing annotation."""
        return self.db.update_annotation(annotation_id, updates)

    def delete_annotation(self, annotation_id: int) -> bool:
        """Delete an annotation."""
        return self.db.delete_annotation(annotation_id)

    def get_annotations(
        self,
        source_id: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        annotation_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get annotations with filters."""
        # Build query based on filters
        query = "SELECT * FROM timeframe_annotations WHERE 1=1"
        params = []

        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)

        if start and end:
            query += " AND start_timestamp <= ? AND end_timestamp >= ?"
            params.extend([end, start])

        if annotation_type:
            query += " AND annotation_type = ?"
            params.append(annotation_type)

        query += " ORDER BY created_at DESC"

        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total_count = self.db.connection.execute(count_query, params).fetchone()[0]

        # Get paginated results
        query += f" LIMIT {limit} OFFSET {offset}"
        results = self.db.connection.execute(query, params).fetchall()

        annotations = []
        for row in results:
            annotations.append(
                {
                    "annotation_id": row[0],
                    "source_id": row[1],
                    "start_timestamp": row[2],
                    "end_timestamp": row[3],
                    "annotation_type": row[4],
                    "content": row[5],
                    "metadata": json.loads(row[6]) if row[6] else None,
                    "created_by": row[7],
                    "created_at": row[8],
                    "updated_at": row[9],
                }
            )

        return {
            "annotations": annotations,
            "count": total_count,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
            },
        }

    def batch_create_annotations(
        self, source_id: int, annotations_data: list[dict[str, Any]]
    ) -> list[int]:
        """Create multiple annotations in batch."""
        from src.storage.models import TimeframeAnnotation

        annotations = []
        for data in annotations_data:
            annotations.append(
                TimeframeAnnotation(
                    source_id=source_id,
                    start_timestamp=data["start_timestamp"],
                    end_timestamp=data["end_timestamp"],
                    annotation_type=data["annotation_type"],
                    content=data["content"],
                    metadata=data.get("metadata"),
                    created_by=data.get("created_by", "system"),
                )
            )
        return self.db.batch_create_annotations(annotations)

    def __del__(self):
        """Cleanup database connection."""
        if hasattr(self, "db"):
            self.db.disconnect()
