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
from src.capture.stream_server import RTMPServer, StreamSession
from src.config import config
from src.storage.db import Database

logger = logging.getLogger(__name__)

# In-memory job tracking (simple for now)
JOBS: dict[str, dict[str, Any]] = {}


class CaptureService:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.path

    def start_capture(
        self, filepath: str, capture_config: Optional[dict[str, Any]] = None
    ) -> str:
        """Start video capture processing and return job ID."""
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
            JOBS[job_id]["status"] = (
                "completed" if result["status"] == "success" else "failed"
            )
            JOBS[job_id]["result"] = result
            JOBS[job_id]["completed_at"] = datetime.now()

        except Exception as e:
            logger.error(f"Capture job {job_id} failed: {e}")
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(e)
            JOBS[job_id]["completed_at"] = datetime.now()

        return job_id

    def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        return JOBS.get(job_id)


class SearchService:
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

        Combines frame entries from timeline table with transcriptions queried
        directly. Transcriptions auto-appear without needing timeline entries.
        """
        # Frame entries from timeline table
        frame_query = """
        SELECT
            t.entry_id,
            t.source_id,
            t.timestamp,
            t.frame_id,
            NULL as transcription_id,
            t.similarity_score,
            f.perceptual_hash,
            f.metadata as frame_metadata,
            NULL as transcript_text,
            NULL as confidence,
            NULL as language,
            NULL as trans_start_timestamp,
            NULL as trans_end_timestamp,
            NULL as speaker_name,
            NULL as speaker_confidence,
            s.source_type,
            s.filename,
            s.location,
            s.device_id,
            s.metadata as source_metadata,
            'frame' as entry_type
        FROM timeline t
        LEFT JOIN frames f ON t.frame_id = f.frame_id
        LEFT JOIN sources s ON t.source_id = s.source_id
        WHERE t.timestamp >= ? AND t.timestamp <= ?
        """
        frame_params = [start, end]
        if source_id:
            frame_query += " AND t.source_id = ?"
            frame_params.append(source_id)

        # Transcription entries directly from transcriptions table
        trans_query = """
        SELECT
            tr.transcription_id as entry_id,
            tr.source_id,
            tr.start_timestamp as timestamp,
            NULL as frame_id,
            tr.transcription_id,
            NULL as similarity_score,
            NULL as perceptual_hash,
            NULL as frame_metadata,
            tr.text as transcript_text,
            tr.confidence,
            tr.language,
            tr.start_timestamp as trans_start_timestamp,
            tr.end_timestamp as trans_end_timestamp,
            tr.speaker_name,
            tr.speaker_confidence,
            s.source_type,
            s.filename,
            s.location,
            s.device_id,
            s.metadata as source_metadata,
            'transcription' as entry_type
        FROM transcriptions tr
        LEFT JOIN sources s ON tr.source_id = s.source_id
        WHERE tr.start_timestamp >= ? AND tr.start_timestamp <= ?
        """
        trans_params = [start, end]
        if source_id:
            trans_query += " AND tr.source_id = ?"
            trans_params.append(source_id)

        # Combine with UNION ALL
        query = f"({frame_query}) UNION ALL ({trans_query}) ORDER BY timestamp LIMIT {limit} OFFSET {offset}"
        params = frame_params + trans_params

        results = self.db.connection.execute(query, params).fetchall()

        # Get ALL annotations for this timeframe (from all sources including voice_notes)
        annotations_by_timestamp = self.db.get_all_annotations_for_timerange(start, end)

        # Voice notes appear automatically via the transcriptions UNION query above.

        entries = []
        for row in results:
            timestamp = row[2]
            entry = {
                "timestamp": timestamp,
                "source_id": row[1],
                "source_type": row[15],  # source_type
                "source_filename": row[16],  # filename
                "source_location": row[17],  # location
                "source_device_id": row[18],  # device_id
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
                    "speaker_name": row[13],
                    "speaker_confidence": row[14],
                }

            entries.append(entry)

        # Sort entries by timestamp
        entries.sort(key=lambda e: e["timestamp"])

        # Get total count (frames from timeline + transcriptions)
        frame_count_query = """
        SELECT COUNT(*) FROM timeline t
        WHERE t.timestamp >= ? AND t.timestamp <= ?
        """
        frame_count_params = [start, end]
        if source_id:
            frame_count_query += " AND t.source_id = ?"
            frame_count_params.append(source_id)

        trans_count_query = """
        SELECT COUNT(*) FROM transcriptions tr
        WHERE tr.start_timestamp >= ? AND tr.start_timestamp <= ?
        """
        trans_count_params = [start, end]
        if source_id:
            trans_count_query += " AND tr.source_id = ?"
            trans_count_params.append(source_id)

        frame_count = self.db.connection.execute(frame_count_query, frame_count_params).fetchone()[0]
        trans_count = self.db.connection.execute(trans_count_query, trans_count_params).fetchone()[0]
        total_count = frame_count + trans_count

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
        """Get frame image data as (bytes, content_type)."""
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
        """Search transcripts by text."""
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

        total_count = self.db.connection.execute(count_query, count_params).fetchone()[
            0
        ]

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
        """Get system status and statistics."""
        stats = self.db.get_statistics()

        # Count active/completed jobs
        active_jobs = sum(
            1 for j in JOBS.values() if j["status"] in ["queued", "processing"]
        )
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
                "deduplication_rate": stats["frames"].get(
                    "deduplication_percentage", 0
                ),
                "size_mb": stats["frames"].get("size_mb", 0),
            },
            "sources": {
                "total": stats["sources"]["total"],
                "total_hours": stats["sources"].get("total_hours", 0),
            },
        }

    def __del__(self):
        if hasattr(self, "db"):
            self.db.disconnect()


class AnnotationService:
    # Class-level cache for user annotations source ID
    _user_annotations_source_id: Optional[int] = None

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.path
        self.db = Database(db_path=self.db_path)
        self.db.connect()

    def get_or_create_user_annotations_source(self) -> int:
        """Get or create a source record for user annotations."""
        if AnnotationService._user_annotations_source_id is not None:
            return AnnotationService._user_annotations_source_id

        # Check if source exists
        result = self.db.connection.execute(
            "SELECT source_id FROM sources WHERE source_type = 'voice_notes' AND filename = 'user_annotations' LIMIT 1"
        ).fetchone()

        if result:
            AnnotationService._user_annotations_source_id = result[0]
            return result[0]

        # Create new source
        from src.storage.models import Source
        now = datetime.utcnow()
        source = Source(
            type="voice_notes",
            filename="user_annotations",
            location="user_created",
            start_timestamp=now,
            end_timestamp=now,
            metadata={"description": "User-created text annotations"},
        )
        source_id = self.db.create_source(source)
        AnnotationService._user_annotations_source_id = source_id
        logger.info(f"Created user annotations source with ID {source_id}")
        return source_id

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


class UserRecordingService:
    """Service for creating user recordings (voice) as transcriptions."""

    # Class-level cache for user recording source ID
    _user_recording_source_id: Optional[int] = None

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.path
        self.db = Database(db_path=self.db_path)
        self.db.connect()
        self._transcriber = None

    @property
    def transcriber(self):
        """Lazy load transcriber to avoid loading model until needed."""
        if self._transcriber is None:
            from src.capture.transcriber import Transcriber
            self._transcriber = Transcriber()
        return self._transcriber

    def _get_or_create_user_recording_source(self) -> int:
        """Get or create a source record for user recordings."""
        if UserRecordingService._user_recording_source_id is not None:
            return UserRecordingService._user_recording_source_id

        # Check if user recording source exists
        result = self.db.connection.execute(
            "SELECT source_id FROM sources WHERE source_type = 'voice_notes' LIMIT 1"
        ).fetchone()

        if result:
            UserRecordingService._user_recording_source_id = result[0]
            return result[0]

        # Create a new source for user recordings
        from src.storage.models import Source
        now = datetime.utcnow()
        source = Source(
            type="voice_notes",
            filename="user_recordings",
            location="user_recorded",
            start_timestamp=now,
            end_timestamp=now,
            metadata={"description": "User-recorded audio transcriptions"},
        )
        source_id = self.db.create_source(source)
        UserRecordingService._user_recording_source_id = source_id
        logger.info(f"Created user recording source with ID {source_id}")
        return source_id

    def create_user_recording(
        self,
        audio_path: Path,
        timestamp: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Create a transcription from user-recorded audio.

        Args:
            audio_path: Path to the audio file
            timestamp: Timestamp to anchor the recording (defaults to now)

        Returns:
            Dictionary with transcription data
        """
        from datetime import timedelta
        from src.storage.models import Transcription

        if timestamp is None:
            timestamp = datetime.utcnow()

        logger.info(f"Creating user recording transcription from {audio_path}")

        # Transcribe with speaker identification
        result = self.transcriber.transcribe_audio(
            audio_path,
            identify_speakers=True
        )

        # Extract primary speaker from segments
        speaker = self._get_primary_speaker(result.get("segments", []))
        speaker_confidence = self._get_speaker_confidence(result.get("segments", []))

        # Build transcription text
        transcription_text = result.get("text", "").strip()

        # Get or create user recording source
        source_id = self._get_or_create_user_recording_source()

        # Calculate end timestamp based on duration
        duration = result.get("duration", 0)
        end_timestamp = timestamp + timedelta(seconds=duration) if duration else timestamp

        # Create Transcription record
        transcription = Transcription(
            source_id=source_id,
            start_timestamp=timestamp,
            end_timestamp=end_timestamp,
            text=transcription_text,
            confidence=result.get("confidence"),
            language=result.get("language", "en"),
            whisper_model=result.get("model", "base"),
            speaker_name=speaker,
            speaker_confidence=speaker_confidence,
        )

        transcription_id = self.db.store_transcription(transcription)

        logger.info(f"Created user recording transcription {transcription_id} with speaker: {speaker}")

        return {
            "transcription_id": transcription_id,
            "transcription": transcription_text,
            "speaker": speaker,
            "timestamp": timestamp.isoformat(),
            "duration": duration,
            "metadata": {
                "duration": duration,
                "language": result.get("language", "en"),
            },
        }

    def _get_primary_speaker(self, segments: list) -> Optional[str]:
        """Extract the primary (most frequent) speaker from segments."""
        if not segments:
            return None

        speaker_counts: dict[str, int] = {}
        for segment in segments:
            speaker = None
            if isinstance(segment, dict):
                speaker = segment.get("speaker")
            elif hasattr(segment, "speaker"):
                speaker = segment.speaker

            if speaker and speaker != "Unknown":
                speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

        if not speaker_counts:
            return None

        return max(speaker_counts, key=speaker_counts.get)

    def _get_speaker_confidence(self, segments: list) -> Optional[float]:
        """Get average speaker confidence from segments."""
        confidences = []
        for segment in segments:
            confidence = None
            if isinstance(segment, dict):
                confidence = segment.get("speaker_confidence")
            elif hasattr(segment, "speaker_confidence"):
                confidence = segment.speaker_confidence

            if confidence is not None:
                confidences.append(confidence)

        if not confidences:
            return None

        return sum(confidences) / len(confidences)

    def transcribe_audio_only(self, audio_path: Path) -> dict[str, Any]:
        """
        Transcribe audio without saving to database.

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary with transcription text and metadata
        """
        logger.info(f"Transcribing audio from {audio_path} (no save)")

        result = self.transcriber.transcribe_audio(
            audio_path,
            identify_speakers=False
        )

        transcription_text = result.get("text", "").strip()

        return {
            "text": transcription_text,
            "language": result.get("language", "en"),
            "duration": result.get("duration", 0),
            "confidence": result.get("confidence"),
        }

    def __del__(self):
        """Cleanup database connection."""
        if hasattr(self, "db"):
            self.db.disconnect()


# Keep VoiceNoteService as alias for backwards compatibility during transition
VoiceNoteService = UserRecordingService


def get_rtmp_server() -> RTMPServer:
    """Get the shared RTMP server instance."""
    global _rtmp_server
    if "_rtmp_server" not in globals():
        _rtmp_server = RTMPServer(
            port=config.streaming.rtmp.port,
            max_streams=config.streaming.rtmp.max_concurrent_streams,
        )
    return _rtmp_server
