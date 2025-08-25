"""Simple SQLite database operations for Mem."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager

from src.storage.models import Source, Frame, Transcription, FrameAnalysis, TranscriptAnalysis
from src.config import config


class Database:
    """Simple SQLite database for storing frames and transcriptions."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self):
        """Connect to the database."""
        self.connection = sqlite3.connect(
            self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.connection.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrency (multiple readers + 1 writer)
        self.connection.execute("PRAGMA journal_mode = WAL")

        # Performance optimizations
        self.connection.execute("PRAGMA synchronous = NORMAL")  # Faster, still safe
        self.connection.execute("PRAGMA cache_size = -64000")  # 64MB cache
        self.connection.execute("PRAGMA mmap_size = 268435456")  # 256MB memory-mapped I/O
        self.connection.execute("PRAGMA temp_store = MEMORY")  # Temp tables in RAM

    def disconnect(self):
        """Disconnect from the database."""
        if self.connection:
            self.connection.close()
            self.connection = None

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def initialize(self):
        """Initialize database with schema."""
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, "r") as f:
            schema = f.read()

        self.connection.executescript(schema)
        self.connection.commit()

    # Source operations
    def create_source(self, source: Source) -> int:
        """Create a new source and return its ID."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sources (type, filename, start_timestamp, end_timestamp, 
                                   duration_seconds, frame_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    source.type,
                    source.filename,
                    source.start_timestamp,
                    source.end_timestamp,
                    source.duration_seconds,
                    source.frame_count,
                    json.dumps(source.metadata) if source.metadata else None,
                ),
            )
            return cursor.lastrowid

    def get_source(self, source_id: int) -> Optional[Source]:
        """Get a source by ID."""
        cursor = self.connection.cursor()
        row = cursor.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()

        if row:
            return Source(
                id=row["id"],
                type=row["type"],
                filename=row["filename"],
                start_timestamp=row["start_timestamp"],
                end_timestamp=row["end_timestamp"],
                duration_seconds=row["duration_seconds"],
                frame_count=row["frame_count"],
                created_at=row["created_at"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
            )
        return None

    def update_source_end(
        self, source_id: int, end_timestamp: datetime, duration_seconds: float, frame_count: int
    ):
        """Update source end time and statistics."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sources 
                SET end_timestamp = ?, duration_seconds = ?, frame_count = ?
                WHERE id = ?
            """,
                (end_timestamp, duration_seconds, frame_count, source_id),
            )

    # Frame operations
    def store_frame(self, frame: Frame) -> int:
        """Store a frame and return its ID."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            frame.size_bytes = len(frame.image_data)

            cursor.execute(
                """
                INSERT INTO frames (source_id, timestamp, image_data, 
                                  width, height, format, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    frame.source_id,
                    frame.timestamp,
                    frame.image_data,
                    frame.width,
                    frame.height,
                    frame.format,
                    frame.size_bytes,
                ),
            )
            return cursor.lastrowid

    def get_frames_by_time_range(
        self, start: datetime, end: datetime, source_id: Optional[int] = None
    ) -> List[Frame]:
        """Get frames within a time range."""
        cursor = self.connection.cursor()

        if source_id:
            query = """
                SELECT * FROM frames 
                WHERE timestamp >= ? AND timestamp <= ? AND source_id = ?
                ORDER BY timestamp
            """
            rows = cursor.execute(query, (start, end, source_id)).fetchall()
        else:
            query = """
                SELECT * FROM frames 
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            """
            rows = cursor.execute(query, (start, end)).fetchall()

        frames = []
        for row in rows:
            frames.append(
                Frame(
                    id=row["id"],
                    source_id=row["source_id"],
                    timestamp=row["timestamp"],
                    image_data=row["image_data"],
                    width=row["width"],
                    height=row["height"],
                    format=row["format"],
                    size_bytes=row["size_bytes"],
                    created_at=row["created_at"],
                )
            )
        return frames

    def get_frame(self, frame_id: int) -> Optional[Frame]:
        """Get a single frame by ID."""
        cursor = self.connection.cursor()
        row = cursor.execute("SELECT * FROM frames WHERE id = ?", (frame_id,)).fetchone()

        if row:
            return Frame(
                id=row["id"],
                source_id=row["source_id"],
                timestamp=row["timestamp"],
                image_data=row["image_data"],
                width=row["width"],
                height=row["height"],
                format=row["format"],
                size_bytes=row["size_bytes"],
                created_at=row["created_at"],
            )
        return None

    # Transcription operations
    def store_transcription(self, transcription: Transcription) -> int:
        """Store a transcription and return its ID."""
        with self.transaction() as conn:
            cursor = conn.cursor()

            # Calculate word count if not provided
            if transcription.word_count is None:
                transcription.word_count = len(transcription.text.split())

            cursor.execute(
                """
                INSERT INTO transcriptions (source_id, start_timestamp, end_timestamp,
                                          text, confidence, language, word_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    transcription.source_id,
                    transcription.start_timestamp,
                    transcription.end_timestamp,
                    transcription.text,
                    transcription.confidence,
                    transcription.language,
                    transcription.word_count,
                ),
            )
            return cursor.lastrowid

    def get_transcriptions_by_time_range(
        self, start: datetime, end: datetime, source_id: Optional[int] = None
    ) -> List[Transcription]:
        """Get transcriptions within a time range."""
        cursor = self.connection.cursor()

        if source_id:
            query = """
                SELECT * FROM transcriptions 
                WHERE start_timestamp <= ? AND end_timestamp >= ? AND source_id = ?
                ORDER BY start_timestamp
            """
            rows = cursor.execute(query, (end, start, source_id)).fetchall()
        else:
            query = """
                SELECT * FROM transcriptions 
                WHERE start_timestamp <= ? AND end_timestamp >= ?
                ORDER BY start_timestamp
            """
            rows = cursor.execute(query, (end, start)).fetchall()

        transcriptions = []
        for row in rows:
            transcriptions.append(
                Transcription(
                    id=row["id"],
                    source_id=row["source_id"],
                    start_timestamp=row["start_timestamp"],
                    end_timestamp=row["end_timestamp"],
                    text=row["text"],
                    confidence=row["confidence"],
                    language=row["language"],
                    word_count=row["word_count"],
                    created_at=row["created_at"],
                )
            )
        return transcriptions

    # Analysis operations
    def store_frame_analysis(self, analysis: FrameAnalysis) -> int:
        """Store frame analysis results."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO frame_analysis (frame_id, model_name, analysis_type,
                                          result, processing_time_ms)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    analysis.frame_id,
                    analysis.model_name,
                    analysis.analysis_type,
                    json.dumps(analysis.result),
                    analysis.processing_time_ms,
                ),
            )
            return cursor.lastrowid

    def store_transcript_analysis(self, analysis: TranscriptAnalysis) -> int:
        """Store transcript analysis results."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO transcript_analysis (transcription_id, model_name, analysis_type,
                                               result, processing_time_ms)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    analysis.transcription_id,
                    analysis.model_name,
                    analysis.analysis_type,
                    json.dumps(analysis.result),
                    analysis.processing_time_ms,
                ),
            )
            return cursor.lastrowid

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.connection.cursor()

        stats = {}

        # Count sources
        stats["sources"] = cursor.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        stats["frames"] = cursor.execute("SELECT COUNT(*) FROM frames").fetchone()[0]
        stats["transcriptions"] = cursor.execute("SELECT COUNT(*) FROM transcriptions").fetchone()[
            0
        ]

        # Storage size
        total_image_size = cursor.execute("SELECT SUM(size_bytes) FROM frames").fetchone()[0] or 0
        stats["total_image_size_mb"] = total_image_size / (1024 * 1024)

        # Time range
        earliest = cursor.execute("SELECT MIN(start_timestamp) FROM sources").fetchone()[0]
        latest = cursor.execute(
            "SELECT MAX(end_timestamp) FROM sources WHERE end_timestamp IS NOT NULL"
        ).fetchone()[0]

        stats["earliest_recording"] = earliest
        stats["latest_recording"] = latest

        return stats
