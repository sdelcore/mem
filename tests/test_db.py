"""Tests for DuckDB storage layer."""

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path


class TestDatabase(unittest.TestCase):
    """Test database operations."""

    def setUp(self):
        """Set up test database."""
        # Import here to avoid module-level import issues
        from src.storage.db import Database
        from src.storage.models import Source

        self.Database = Database
        self.Source = Source

        # Create temporary database with unique name
        import uuid

        temp_dir = tempfile.gettempdir()
        self.db_path = os.path.join(temp_dir, f"test_{uuid.uuid4().hex}.duckdb")

        # Ensure file doesn't exist
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

        self.db = self.Database(self.db_path)
        self.db.connect()
        self.db.initialize()

    def tearDown(self):
        """Clean up test database."""
        self.db.disconnect()
        os.unlink(self.db_path)

    def test_connection(self):
        """Test database connection."""
        self.assertIsNotNone(self.db.connection)

    def test_initialize_schema(self):
        """Test schema initialization."""
        # Schema should already be initialized by setUp
        # Try to create a source to verify tables exist
        source = self.Source(type="video", filename="test.mp4", start_timestamp=datetime.utcnow())
        source_id = self.db.create_source(source)
        self.assertGreater(source_id, 0)

    def test_create_source(self):
        """Test source creation."""
        now = datetime.utcnow()
        source = self.Source(
            type="video",
            filename="test_video.mp4",
            location="office",
            device_id="cam1",
            start_timestamp=now,
            fps=30.0,
            width=1920,
            height=1080,
            metadata={"codec": "h264"},
        )

        source_id = self.db.create_source(source)
        self.assertGreater(source_id, 0)

        # Verify source was created
        sources = self.db.get_sources()
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].filename, "test_video.mp4")
        self.assertEqual(sources[0].location, "office")

    def test_store_frame(self):
        """Test storing unique frames."""
        from src.storage.models import Frame

        # Create source first
        source = self.Source(type="video", filename="test.mp4", start_timestamp=datetime.utcnow())
        source_id = self.db.create_source(source)

        # Create frame
        now = datetime.utcnow()
        frame = Frame(
            source_id=source_id,
            first_seen_timestamp=now,
            last_seen_timestamp=now,
            perceptual_hash="abc123",
            image_data=b"fake_jpeg_data",
            width=640,
            height=480,
            jpeg_quality=85,
        )

        frame_id = self.db.store_frame(frame)
        self.assertGreater(frame_id, 0)

        # Verify frame was stored
        retrieved = self.db.get_frame(frame_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.perceptual_hash, "abc123")
        # Width is now in metadata
        if retrieved.metadata:
            self.assertEqual(retrieved.metadata.get("width"), 640)

    def test_find_similar_frame(self):
        """Test finding frames by perceptual hash."""
        from src.storage.models import Frame

        # Create source
        source = self.Source(type="video", filename="test.mp4", start_timestamp=datetime.utcnow())
        source_id = self.db.create_source(source)

        # Store frame
        frame = Frame(
            source_id=source_id,
            first_seen_timestamp=datetime.utcnow(),
            last_seen_timestamp=datetime.utcnow(),
            perceptual_hash="hash123",
            image_data=b"data",
            width=640,
            height=480,
        )
        frame_id = self.db.store_frame(frame)

        # Find by hash
        found_id = self.db.find_similar_frame(source_id, "hash123")
        self.assertEqual(found_id, frame_id)

        # Not found case
        not_found = self.db.find_similar_frame(source_id, "nonexistent")
        self.assertIsNone(not_found)

    def test_create_timeline_entry(self):
        """Test timeline entry creation."""
        from src.storage.models import Timeline

        # Create source
        source = self.Source(type="video", filename="test.mp4", start_timestamp=datetime.utcnow())
        source_id = self.db.create_source(source)

        # Create timeline entry
        timeline = Timeline(
            source_id=source_id,
            timestamp=datetime.utcnow(),
            frame_id=None,
            similarity_score=95.5,
            scene_changed=False,
        )

        entry_id = self.db.create_timeline_entry(timeline)
        self.assertGreater(entry_id, 0)

    def test_store_transcription(self):
        """Test transcription storage."""
        from src.storage.models import Transcription

        # Create source
        source = self.Source(type="video", filename="test.mp4", start_timestamp=datetime.utcnow())
        source_id = self.db.create_source(source)

        # Create transcription
        now = datetime.utcnow()
        transcription = Transcription(
            source_id=source_id,
            start_timestamp=now,
            end_timestamp=now + timedelta(seconds=10),
            text="Hello world",
            confidence=0.95,
            language="en",
            whisper_model="base",
        )

        trans_id = self.db.store_transcription(transcription)
        self.assertGreater(trans_id, 0)

        # Verify word count was calculated
        trans_list = self.db.get_transcriptions_by_time_range(
            now - timedelta(seconds=1), now + timedelta(seconds=11)
        )
        self.assertEqual(len(trans_list), 1)
        self.assertEqual(trans_list[0].word_count, 2)

    def test_get_statistics(self):
        """Test database statistics."""
        # Create test data
        now = datetime.utcnow()
        source = self.Source(
            type="video",
            filename="test.mp4",
            start_timestamp=now,
            end_timestamp=now + timedelta(seconds=3600),  # 1 hour
        )
        source_id = self.db.create_source(source)

        # Get stats
        stats = self.db.get_statistics()

        self.assertEqual(stats["sources"]["total"], 1)
        self.assertEqual(stats["sources"]["total_hours"], 1.0)

    def test_reset_database(self):
        """Test database reset."""
        # Create some data
        source = self.Source(type="video", filename="test.mp4", start_timestamp=datetime.utcnow())
        source_id = self.db.create_source(source)

        # Reset database
        self.db.reset_database()

        # Verify empty
        sources = self.db.get_sources()
        self.assertEqual(len(sources), 0)

        # Can still create new data
        new_source = self.Source(
            type="video", filename="new.mp4", start_timestamp=datetime.utcnow()
        )
        new_id = self.db.create_source(new_source)
        self.assertGreater(new_id, 0)


if __name__ == "__main__":
    unittest.main()
