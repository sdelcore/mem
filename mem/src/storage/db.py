"""DuckDB storage layer for mem project."""

import json
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import duckdb

from src.storage.models import Frame, Source, Timeline, Transcription

logger = logging.getLogger(__name__)


class Database:
    """DuckDB database interface for time-series multimedia storage."""

    def __init__(self, db_path: str = "mem.duckdb"):
        """
        Initialize database connection.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Connect to DuckDB database with optimized settings."""
        try:
            # Check if this is a new database
            is_new_db = not Path(self.db_path).exists()

            self.connection = duckdb.connect(self.db_path)

            # Performance optimizations
            self.connection.execute("SET memory_limit='4GB'")
            self.connection.execute("SET threads=4")

            logger.info(f"Connected to DuckDB database at {self.db_path}")

            # Initialize schema if this is a new database
            if is_new_db or not self._schema_exists():
                logger.info("Database is new or schema missing, initializing...")
                self.initialize()

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Disconnected from database")

    def _schema_exists(self) -> bool:
        """Check if the database schema exists."""
        try:
            # Check if the sources table exists (as a proxy for schema existence)
            result = self.connection.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'sources'"
            ).fetchone()
            return result[0] > 0
        except Exception:
            return False

    def initialize(self):
        """Create database schema if not exists."""
        schema_path = Path(__file__).parent / "schema.sql"

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path) as f:
            schema_sql = f.read()

        try:
            self.connection.execute(schema_sql)
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            yield self.connection
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Transaction failed: {e}")
            raise

    # Source operations
    def create_source(self, source: Source) -> int:
        """
        Create a new source record.

        Args:
            source: Source model instance

        Returns:
            Generated source_id
        """
        with self.transaction() as conn:
            result = conn.execute(
                """
                INSERT INTO sources (
                    source_type, filename, location, device_id,
                    start_timestamp, end_timestamp, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING source_id
                """,
                [
                    source.type,
                    source.filename,
                    source.location,
                    source.device_id,
                    source.start_timestamp,
                    source.end_timestamp,
                    json.dumps(source.metadata) if source.metadata else None,
                ],
            )
            source_id = result.fetchone()[0]
            logger.info(f"Created source {source_id} for {source.filename}")
            return source_id

    def update_source_end(self, source_id: int, end_timestamp: datetime, duration: float):
        """Update source end timestamp."""
        self.connection.execute(
            """
            UPDATE sources
            SET end_timestamp = ?
            WHERE source_id = ?
            """,
            [end_timestamp, source_id],
        )

    # Frame operations with deduplication
    def store_frame(self, frame: Frame) -> int:
        """
        Store a new frame.

        Args:
            frame: Frame model instance

        Returns:
            Generated frame_id
        """
        with self.transaction() as conn:
            result = conn.execute(
                """
                INSERT INTO frames (
                    source_id, first_seen_timestamp, last_seen_timestamp,
                    perceptual_hash, image_data, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
                RETURNING frame_id
                """,
                [
                    frame.source_id,
                    frame.first_seen_timestamp,
                    frame.last_seen_timestamp,
                    frame.perceptual_hash,
                    frame.image_data,
                    json.dumps(frame.metadata) if frame.metadata else None,
                ],
            )
            return result.fetchone()[0]

    def find_similar_frame(self, source_id: int, perceptual_hash: str) -> Optional[int]:
        """
        Find existing frame with same hash.

        Args:
            source_id: Source identifier
            perceptual_hash: Hash to search for

        Returns:
            frame_id if found, None otherwise
        """
        result = self.connection.execute(
            """
            SELECT frame_id FROM frames
            WHERE source_id = ? AND perceptual_hash = ?
            LIMIT 1
            """,
            [source_id, perceptual_hash],
        )
        row = result.fetchone()
        return row[0] if row else None

    def update_frame_last_seen(self, frame_id: int, timestamp: datetime):
        """Update the last seen timestamp for a frame."""
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE frames
                SET last_seen_timestamp = ?
                WHERE frame_id = ?
                """,
                [timestamp, frame_id],
            )

    def get_frame(self, frame_id: int) -> Optional[Frame]:
        """Get a single frame by ID."""
        row = self.connection.execute(
            "SELECT * FROM frames WHERE frame_id = ?", [frame_id]
        ).fetchone()

        if row:
            return Frame(
                frame_id=row[0],
                source_id=row[1],
                first_seen_timestamp=row[2],
                last_seen_timestamp=row[3],
                perceptual_hash=row[4],
                image_data=row[5],
                metadata=json.loads(row[6]) if row[6] else None,
            )
        return None

    def get_frames_by_time_range(
        self, start: datetime, end: datetime, source_id: Optional[int] = None
    ) -> list[Frame]:
        """Get frames within a time range."""
        query = """
            SELECT DISTINCT f.* FROM frames f
            JOIN timeline t ON f.frame_id = t.frame_id
            WHERE t.timestamp >= ? AND t.timestamp <= ?
        """
        params = [start, end]

        if source_id:
            query += " AND f.source_id = ?"
            params.append(source_id)

        query += " ORDER BY f.first_seen_timestamp"

        result = self.connection.execute(query, params)
        frames = []
        for row in result.fetchall():
            frames.append(
                Frame(
                    frame_id=row[0],
                    source_id=row[1],
                    first_seen_timestamp=row[2],
                    last_seen_timestamp=row[3],
                    perceptual_hash=row[4],
                    image_data=row[5],
                    metadata=json.loads(row[6]) if row[6] else None,
                )
            )
        return frames

    # Timeline operations
    def create_timeline_entry(self, timeline: Timeline) -> int:
        """
        Create timeline entry mapping timestamp to data.

        Args:
            timeline: Timeline model instance

        Returns:
            Generated entry_id
        """
        with self.transaction() as conn:
            result = conn.execute(
                """
                INSERT INTO timeline (
                    source_id, timestamp, frame_id, transcription_id,
                    similarity_score
                ) VALUES (?, ?, ?, ?, ?)
                RETURNING entry_id
                """,
                [
                    timeline.source_id,
                    timeline.timestamp,
                    timeline.frame_id,
                    timeline.transcription_id,
                    timeline.similarity_score,
                ],
            )
            return result.fetchone()[0]

    def get_active_transcription(self, source_id: int, timestamp: datetime) -> Optional[int]:
        """
        Get transcription active at given timestamp.

        Args:
            source_id: Source identifier
            timestamp: Query timestamp

        Returns:
            transcription_id if found
        """
        result = self.connection.execute(
            """
            SELECT transcription_id FROM transcriptions
            WHERE source_id = ?
                AND start_timestamp <= ?
                AND end_timestamp >= ?
            LIMIT 1
            """,
            [source_id, timestamp, timestamp],
        )
        row = result.fetchone()
        return row[0] if row else None

    # Transcription operations
    def store_transcription(self, transcription: Transcription) -> int:
        """
        Store transcription segment.

        Args:
            transcription: Transcription model instance

        Returns:
            Generated transcription_id
        """
        with self.transaction() as conn:
            result = conn.execute(
                """
                INSERT INTO transcriptions (
                    source_id, start_timestamp, end_timestamp,
                    text, confidence, language, whisper_model
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING transcription_id
                """,
                [
                    transcription.source_id,
                    transcription.start_timestamp,
                    transcription.end_timestamp,
                    transcription.text,
                    transcription.confidence,
                    transcription.language,
                    transcription.whisper_model,
                ],
            )
            return result.fetchone()[0]

    # Query operations
    def get_timeline_range(
        self,
        start: datetime,
        end: datetime,
        source_id: Optional[int] = None,
        include_unchanged: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get timeline entries for time range.

        Args:
            start: Start timestamp
            end: End timestamp
            source_id: Optional source filter
            include_unchanged: Include entries where scene hasn't changed

        Returns:
            List of timeline entries with associated data
        """
        query = """
            SELECT
                t.entry_id,
                t.timestamp,
                t.source_id,
                s.location,
                s.filename,
                t.frame_id,
                t.similarity_score,
                tr.text as transcript_text,
                tr.confidence as transcript_confidence
            FROM timeline t
            JOIN sources s ON t.source_id = s.source_id
            LEFT JOIN transcriptions tr
                ON t.transcription_id = tr.transcription_id
            WHERE t.timestamp >= ? AND t.timestamp <= ?
        """
        params = [start, end]

        if source_id:
            query += " AND t.source_id = ?"
            params.append(source_id)

        if not include_unchanged:
            query += " AND t.similarity_score < 95.0"

        query += " ORDER BY t.timestamp, t.source_id"

        result = self.connection.execute(query, params)

        entries = []
        for row in result.fetchall():
            entries.append(
                {
                    "entry_id": row[0],
                    "timestamp": row[1],
                    "source_id": row[2],
                    "location": row[3],
                    "filename": row[4],
                    "frame_id": row[5],
                    "similarity_score": row[6],
                    "scene_changed": row[6] < 95.0 if row[6] is not None else False,
                    "transcript_text": row[7],
                    "transcript_confidence": row[8],
                }
            )

        return entries

    def get_temporal_summary(
        self, start: datetime, end: datetime, bucket_size: str = "5 minutes"
    ) -> list[dict[str, Any]]:
        """
        Get temporal summary using TIME_BUCKET.

        Args:
            start: Start timestamp
            end: End timestamp
            bucket_size: Time bucket size (e.g., '5 minutes', '1 hour')

        Returns:
            Aggregated summary by time bucket
        """
        query = """
            SELECT
                time_bucket(INTERVAL ?, timestamp) as bucket,
                source_id,
                COUNT(DISTINCT frame_id) as unique_frames,
                COUNT(*) as total_entries,
                AVG(similarity_score) as avg_similarity,
                SUM(CASE WHEN similarity_score < 95.0 THEN 1 ELSE 0 END) as scene_changes
            FROM timeline
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY bucket, source_id
            ORDER BY bucket, source_id
        """

        result = self.connection.execute(query, [bucket_size, start, end])

        summaries = []
        for row in result.fetchall():
            summaries.append(
                {
                    "bucket": row[0],
                    "source_id": row[1],
                    "unique_frames": row[2],
                    "total_entries": row[3],
                    "avg_similarity": row[4],
                    "scene_changes": row[5],
                }
            )

        return summaries

    def get_transcriptions_by_time_range(
        self, start: datetime, end: datetime, source_id: Optional[int] = None
    ) -> list[Transcription]:
        """Get transcriptions within time range."""
        query = """
            SELECT * FROM transcriptions
            WHERE start_timestamp <= ? AND end_timestamp >= ?
        """
        params = [end, start]

        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)

        query += " ORDER BY start_timestamp"

        result = self.connection.execute(query, params)

        transcriptions = []
        for row in result.fetchall():
            transcriptions.append(
                Transcription(
                    transcription_id=row[0],
                    source_id=row[1],
                    start_timestamp=row[2],
                    end_timestamp=row[3],
                    text=row[4],
                    confidence=row[5],
                    language=row[6],
                    whisper_model=row[7],
                )
            )

        return transcriptions

    def update_frame_last_seen(self, frame_id: int, timestamp: datetime) -> None:
        """
        Update the last seen timestamp for a unique frame.

        Args:
            frame_id: Frame ID to update
            timestamp: New last seen timestamp
        """
        query = """
        UPDATE unique_frames
        SET last_seen_timestamp = ?
        WHERE frame_id = ?
        """
        self.connection.execute(query, [timestamp, frame_id])
        self.connection.commit()

    def update_timeline_transcriptions(
        self,
        source_id: int,
        start_time: datetime,
        end_time: datetime,
        transcription_id: int,
    ) -> None:
        """
        Update timeline entries to reference a transcription.

        Args:
            source_id: Source ID
            start_time: Start of transcription time range
            end_time: End of transcription time range
            transcription_id: Transcription ID to reference
        """
        query = """
        UPDATE timeline
        SET transcription_id = ?
        WHERE source_id = ?
          AND timestamp >= ?
          AND timestamp <= ?
        """
        self.connection.execute(query, [transcription_id, source_id, start_time, end_time])
        self.connection.commit()

    def get_unique_frame_count(self, source_id: int) -> int:
        """
        Get count of unique frames for a source.

        Args:
            source_id: Source ID

        Returns:
            Number of unique frames
        """
        query = "SELECT COUNT(*) FROM unique_frames WHERE source_id = ?"
        result = self.connection.execute(query, [source_id]).fetchone()
        return result[0] if result else 0

    def get_statistics(self) -> dict[str, Any]:
        """Get database statistics."""
        stats = {}

        # Source statistics
        source_stats = self.connection.execute(
            """
            SELECT
                COUNT(*) as total_sources,
                COUNT(DISTINCT location) as unique_locations,
                SUM(EXTRACT(EPOCH FROM (end_timestamp - start_timestamp))) / 3600.0 as total_hours
            FROM sources
            WHERE end_timestamp IS NOT NULL
        """
        ).fetchone()

        stats["sources"] = {
            "total": source_stats[0],
            "locations": source_stats[1],
            "total_hours": round(source_stats[2] or 0, 2),
        }

        # Frame statistics with deduplication info
        frame_stats = self.connection.execute(
            """
            SELECT
                COUNT(DISTINCT uf.frame_id) as unique_frames,
                COUNT(t.entry_id) as total_timeline_entries,
                SUM(OCTET_LENGTH(uf.image_data)) / (1024.0 * 1024.0) as total_size_mb
            FROM unique_frames uf
            LEFT JOIN timeline t ON uf.frame_id = t.frame_id
        """
        ).fetchone()

        # Calculate average references
        avg_refs = 0
        if frame_stats[0] and frame_stats[1]:
            avg_refs = frame_stats[1] / frame_stats[0]

        stats["frames"] = {
            "unique": frame_stats[0] or 0,
            "total_references": frame_stats[1] or 0,
            "size_mb": round(frame_stats[2] or 0, 2),
            "avg_references": round(avg_refs, 2),
        }

        # Calculate deduplication ratio
        if frame_stats[1] > 0:
            dedup_ratio = (1 - frame_stats[0] / frame_stats[1]) * 100
            stats["frames"]["deduplication_percentage"] = round(dedup_ratio, 2)

        # Transcription statistics
        trans_stats = self.connection.execute(
            """
            SELECT
                COUNT(*) as total_segments,
                SUM(array_length(string_split(text, ' '), 1)) as total_words,
                COUNT(DISTINCT language) as languages
            FROM transcriptions
        """
        ).fetchone()

        stats["transcriptions"] = {
            "segments": trans_stats[0] or 0,
            "words": trans_stats[1] or 0,
            "languages": trans_stats[2] or 0,
        }

        return stats

    def get_source(self, source_id: int) -> Optional[Source]:
        """Get a specific source by ID."""
        result = self.connection.execute("SELECT * FROM sources WHERE source_id = ?", [source_id])

        row = result.fetchone()
        if row:
            return Source(
                id=row[0],
                type=row[1],
                filename=row[2],
                location=row[3],
                device_id=row[4],
                start_timestamp=row[5],
                end_timestamp=row[6],
                metadata=json.loads(row[7]) if row[7] else None,
                created_at=row[8],
            )
        return None

    def get_sources(self) -> list[Source]:
        """Get all sources."""
        result = self.connection.execute("SELECT * FROM sources ORDER BY start_timestamp DESC")

        sources = []
        for row in result.fetchall():
            sources.append(
                Source(
                    id=row[0],
                    type=row[1],
                    filename=row[2],
                    location=row[3],
                    device_id=row[4],
                    start_timestamp=row[5],
                    end_timestamp=row[6],
                    metadata=json.loads(row[7]) if row[7] else None,
                    created_at=row[8],
                )
            )

        return sources

    # Annotation operations
    def create_annotation(self, annotation: "TimeframeAnnotation") -> int:
        """
        Create a new annotation.

        Args:
            annotation: TimeframeAnnotation to create

        Returns:
            annotation_id of created annotation
        """
        with self.transaction() as conn:
            result = conn.execute(
                """
                INSERT INTO timeframe_annotations (
                    source_id, start_timestamp, end_timestamp,
                    annotation_type, content, metadata, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING annotation_id
                """,
                [
                    annotation.source_id,
                    annotation.start_timestamp,
                    annotation.end_timestamp,
                    annotation.annotation_type,
                    annotation.content,
                    json.dumps(annotation.metadata) if annotation.metadata else None,
                    annotation.created_by,
                ],
            )
            annotation_id = result.fetchone()[0]
            logger.info(f"Created annotation {annotation_id} for source {annotation.source_id}")
            return annotation_id

    def update_annotation(self, annotation_id: int, updates: dict[str, Any]) -> bool:
        """
        Update an existing annotation.

        Args:
            annotation_id: ID of annotation to update
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if not found
        """
        allowed_fields = ["content", "metadata", "annotation_type", "updated_at"]
        update_fields = []
        values = []

        for field, value in updates.items():
            if field in allowed_fields:
                if field == "metadata":
                    value = json.dumps(value) if value else None
                update_fields.append(f"{field} = ?")
                values.append(value)

        if not update_fields:
            return False

        # Always update the updated_at timestamp
        update_fields.append("updated_at = current_timestamp")

        with self.transaction() as conn:
            values.append(annotation_id)
            result = conn.execute(
                f"""
                UPDATE timeframe_annotations
                SET {', '.join(update_fields)}
                WHERE annotation_id = ?
                """,
                values,
            )
            return result.rowcount > 0

    def delete_annotation(self, annotation_id: int) -> bool:
        """
        Delete an annotation.

        Args:
            annotation_id: ID of annotation to delete

        Returns:
            True if deleted, False if not found
        """
        with self.transaction() as conn:
            result = conn.execute(
                "DELETE FROM timeframe_annotations WHERE annotation_id = ?",
                [annotation_id],
            )
            return result.rowcount > 0

    def get_annotations_for_timeframe(
        self,
        source_id: int,
        start: datetime,
        end: datetime,
        annotation_type: Optional[str] = None,
    ) -> list["TimeframeAnnotation"]:
        """
        Get annotations that overlap with a timeframe.

        Args:
            source_id: Source to query
            start: Start timestamp
            end: End timestamp
            annotation_type: Optional filter by type

        Returns:
            List of annotations
        """
        query = """
            SELECT * FROM timeframe_annotations
            WHERE source_id = ?
                AND start_timestamp <= ?
                AND end_timestamp >= ?
        """
        params = [source_id, end, start]

        if annotation_type:
            query += " AND annotation_type = ?"
            params.append(annotation_type)

        query += " ORDER BY start_timestamp"

        result = self.connection.execute(query, params)

        from src.storage.models import TimeframeAnnotation

        annotations = []
        for row in result:
            annotations.append(
                TimeframeAnnotation(
                    annotation_id=row[0],
                    source_id=row[1],
                    start_timestamp=row[2],
                    end_timestamp=row[3],
                    annotation_type=row[4],
                    content=row[5],
                    metadata=json.loads(row[6]) if row[6] else None,
                    created_by=row[7],
                    created_at=row[8],
                    updated_at=row[9],
                )
            )
        return annotations

    def get_annotations_for_timeline(
        self, source_id: int, start: datetime, end: datetime
    ) -> dict[datetime, list["TimeframeAnnotation"]]:
        """
        Get annotations grouped by timeline timestamps.

        This is optimized for timeline queries where we need to match
        annotations to specific timestamps.

        Args:
            source_id: Source to query
            start: Start timestamp
            end: End timestamp

        Returns:
            Dictionary mapping timestamps to their annotations
        """
        query = """
            SELECT 
                a.*,
                t.timestamp
            FROM timeframe_annotations a
            CROSS JOIN timeline t
            WHERE a.source_id = ?
                AND t.source_id = a.source_id
                AND t.timestamp >= ?
                AND t.timestamp <= ?
                AND t.timestamp >= a.start_timestamp
                AND t.timestamp <= a.end_timestamp
            ORDER BY t.timestamp, a.created_at DESC
        """

        result = self.connection.execute(query, [source_id, start, end]).fetchall()

        from src.storage.models import TimeframeAnnotation

        annotations_by_timestamp = {}
        for row in result:
            timestamp = row[10]  # The joined timestamp from timeline
            annotation = TimeframeAnnotation(
                annotation_id=row[0],
                source_id=row[1],
                start_timestamp=row[2],
                end_timestamp=row[3],
                annotation_type=row[4],
                content=row[5],
                metadata=json.loads(row[6]) if row[6] else None,
                created_by=row[7],
                created_at=row[8],
                updated_at=row[9],
            )

            if timestamp not in annotations_by_timestamp:
                annotations_by_timestamp[timestamp] = []
            annotations_by_timestamp[timestamp].append(annotation)

        return annotations_by_timestamp

    def batch_create_annotations(self, annotations: list["TimeframeAnnotation"]) -> list[int]:
        """
        Create multiple annotations in a single transaction.

        Args:
            annotations: List of annotations to create

        Returns:
            List of created annotation IDs
        """
        annotation_ids = []
        with self.transaction() as conn:
            for annotation in annotations:
                result = conn.execute(
                    """
                    INSERT INTO timeframe_annotations (
                        source_id, start_timestamp, end_timestamp,
                        annotation_type, content, metadata, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    RETURNING annotation_id
                    """,
                    [
                        annotation.source_id,
                        annotation.start_timestamp,
                        annotation.end_timestamp,
                        annotation.annotation_type,
                        annotation.content,
                        (json.dumps(annotation.metadata) if annotation.metadata else None),
                        annotation.created_by,
                    ],
                )
                annotation_ids.append(result.fetchone()[0])

            logger.info(f"Created {len(annotation_ids)} annotations in batch")
        return annotation_ids

    def reset_database(self):
        """Drop and recreate all tables."""
        # Drop views first
        self.connection.execute("DROP VIEW IF EXISTS deduplication_stats")
        self.connection.execute("DROP VIEW IF EXISTS scene_changes")
        self.connection.execute("DROP VIEW IF EXISTS current_state")

        # Drop tables in reverse dependency order
        self.connection.execute("DROP TABLE IF EXISTS timeline")
        self.connection.execute("DROP TABLE IF EXISTS transcriptions")
        self.connection.execute("DROP TABLE IF EXISTS timeframe_annotations")
        self.connection.execute("DROP TABLE IF EXISTS unique_frames")
        self.connection.execute("DROP TABLE IF EXISTS sources")

        # Recreate schema
        self.initialize()
        logger.info("Database reset complete")
