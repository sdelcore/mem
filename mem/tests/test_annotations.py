"""Tests for annotation functionality."""

import json
import unittest
from datetime import datetime, timedelta

from src.storage.db import Database
from src.storage.models import Source, TimeframeAnnotation


class TestAnnotationModels(unittest.TestCase):
    """Test annotation models."""

    def test_timeframe_annotation_model(self):
        """Test TimeframeAnnotation model creation and validation."""
        annotation = TimeframeAnnotation(
            source_id=1,
            start_timestamp=datetime(2025, 8, 22, 14, 0, 0),
            end_timestamp=datetime(2025, 8, 22, 14, 30, 0),
            annotation_type="user_note",
            content="Test annotation content",
            metadata={"key": "value"},
            created_by="test_user",
        )

        self.assertEqual(annotation.source_id, 1)
        self.assertEqual(annotation.annotation_type, "user_note")
        self.assertEqual(annotation.content, "Test annotation content")
        self.assertEqual(annotation.duration_seconds, 1800.0)  # 30 minutes
        self.assertEqual(annotation.created_by, "test_user")

    def test_annotation_type_validation(self):
        """Test that annotation type is validated."""
        valid_types = [
            "user_note",
            "ai_summary",
            "ocr_output",
            "llm_query",
            "scene_description",
            "action_detected",
            "custom",
        ]

        for atype in valid_types:
            annotation = TimeframeAnnotation(
                source_id=1,
                start_timestamp=datetime.utcnow(),
                end_timestamp=datetime.utcnow() + timedelta(minutes=5),
                annotation_type=atype,
                content="Test",
            )
            self.assertEqual(annotation.annotation_type, atype)


class TestAnnotationDatabase(unittest.TestCase):
    """Test annotation database operations."""

    def setUp(self):
        """Set up test database."""
        import uuid

        self.db_path = f"/tmp/test_annotations_{uuid.uuid4().hex}.duckdb"
        self.db = Database(self.db_path)
        self.db.connect()
        self.db.initialize()

        # Create a test source
        source = Source(
            type="video",
            filename="2025-08-22_14-00-00.mp4",
            location="/test/video.mp4",
            start_timestamp=datetime(2025, 8, 22, 14, 0, 0),
            end_timestamp=datetime(2025, 8, 22, 15, 0, 0),
        )
        self.source_id = self.db.create_source(source)

    def tearDown(self):
        """Clean up test database."""
        self.db.disconnect()
        import os

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_annotation(self):
        """Test creating an annotation."""
        annotation = TimeframeAnnotation(
            source_id=self.source_id,
            start_timestamp=datetime(2025, 8, 22, 14, 10, 0),
            end_timestamp=datetime(2025, 8, 22, 14, 15, 0),
            annotation_type="user_note",
            content="Test note",
            metadata={"tags": ["test"]},
            created_by="test_user",
        )

        annotation_id = self.db.create_annotation(annotation)
        self.assertIsNotNone(annotation_id)
        self.assertGreater(annotation_id, 0)

    def test_update_annotation(self):
        """Test updating an annotation."""
        # Create annotation
        annotation = TimeframeAnnotation(
            source_id=self.source_id,
            start_timestamp=datetime(2025, 8, 22, 14, 10, 0),
            end_timestamp=datetime(2025, 8, 22, 14, 15, 0),
            annotation_type="user_note",
            content="Original content",
        )
        annotation_id = self.db.create_annotation(annotation)

        # Update it
        updates = {
            "content": "Updated content",
            "metadata": {"updated": True},
        }
        success = self.db.update_annotation(annotation_id, updates)
        self.assertTrue(success)

        # Verify update
        result = self.db.connection.execute(
            "SELECT content, metadata FROM timeframe_annotations WHERE annotation_id = ?",
            [annotation_id],
        ).fetchone()
        self.assertEqual(result[0], "Updated content")
        self.assertEqual(json.loads(result[1])["updated"], True)

    def test_delete_annotation(self):
        """Test deleting an annotation."""
        # Create annotation
        annotation = TimeframeAnnotation(
            source_id=self.source_id,
            start_timestamp=datetime(2025, 8, 22, 14, 10, 0),
            end_timestamp=datetime(2025, 8, 22, 14, 15, 0),
            annotation_type="user_note",
            content="To be deleted",
        )
        annotation_id = self.db.create_annotation(annotation)

        # Delete it
        success = self.db.delete_annotation(annotation_id)
        self.assertTrue(success)

        # Verify deletion
        result = self.db.connection.execute(
            "SELECT COUNT(*) FROM timeframe_annotations WHERE annotation_id = ?",
            [annotation_id],
        ).fetchone()
        self.assertEqual(result[0], 0)

    def test_get_annotations_for_timeframe(self):
        """Test getting annotations for a timeframe."""
        # Create multiple annotations
        for i in range(3):
            annotation = TimeframeAnnotation(
                source_id=self.source_id,
                start_timestamp=datetime(2025, 8, 22, 14, i * 10, 0),
                end_timestamp=datetime(2025, 8, 22, 14, i * 10 + 5, 0),
                annotation_type="user_note",
                content=f"Note {i}",
            )
            self.db.create_annotation(annotation)

        # Query overlapping timeframe
        annotations = self.db.get_annotations_for_timeframe(
            self.source_id,
            start=datetime(2025, 8, 22, 14, 5, 0),
            end=datetime(2025, 8, 22, 14, 15, 0),
        )

        # Should get annotations that overlap with 14:05-14:15
        self.assertEqual(len(annotations), 2)  # Notes 0 and 1

    def test_get_annotations_by_type(self):
        """Test filtering annotations by type."""
        # Create annotations of different types
        types = ["user_note", "ai_summary", "ocr_output"]
        for atype in types:
            annotation = TimeframeAnnotation(
                source_id=self.source_id,
                start_timestamp=datetime(2025, 8, 22, 14, 0, 0),
                end_timestamp=datetime(2025, 8, 22, 14, 5, 0),
                annotation_type=atype,
                content=f"Content for {atype}",
            )
            self.db.create_annotation(annotation)

        # Query specific type
        annotations = self.db.get_annotations_for_timeframe(
            self.source_id,
            start=datetime(2025, 8, 22, 14, 0, 0),
            end=datetime(2025, 8, 22, 15, 0, 0),
            annotation_type="ai_summary",
        )

        self.assertEqual(len(annotations), 1)
        self.assertEqual(annotations[0].annotation_type, "ai_summary")

    def test_batch_create_annotations(self):
        """Test batch creation of annotations."""
        annotations = []
        for i in range(5):
            annotations.append(
                TimeframeAnnotation(
                    source_id=self.source_id,
                    start_timestamp=datetime(2025, 8, 22, 14, i * 5, 0),
                    end_timestamp=datetime(2025, 8, 22, 14, i * 5 + 3, 0),
                    annotation_type="ai_summary",
                    content=f"Batch annotation {i}",
                    metadata={"batch": True, "index": i},
                )
            )

        annotation_ids = self.db.batch_create_annotations(annotations)

        self.assertEqual(len(annotation_ids), 5)
        for aid in annotation_ids:
            self.assertGreater(aid, 0)

        # Verify all were created
        count = self.db.connection.execute(
            "SELECT COUNT(*) FROM timeframe_annotations WHERE source_id = ?",
            [self.source_id],
        ).fetchone()[0]
        self.assertEqual(count, 5)

    def test_annotations_for_timeline(self):
        """Test getting annotations grouped by timeline timestamps."""
        # Create timeline entries
        for i in range(3):
            timestamp = datetime(2025, 8, 22, 14, i * 10, 0)
            self.db.connection.execute(
                "INSERT INTO timeline (source_id, timestamp) VALUES (?, ?)",
                [self.source_id, timestamp],
            )

        # Create annotations that overlap with timeline entries
        annotation1 = TimeframeAnnotation(
            source_id=self.source_id,
            start_timestamp=datetime(2025, 8, 22, 13, 55, 0),
            end_timestamp=datetime(2025, 8, 22, 14, 5, 0),  # Covers 14:00
            annotation_type="user_note",
            content="First note",
        )
        self.db.create_annotation(annotation1)

        annotation2 = TimeframeAnnotation(
            source_id=self.source_id,
            start_timestamp=datetime(2025, 8, 22, 14, 8, 0),
            end_timestamp=datetime(2025, 8, 22, 14, 12, 0),  # Covers 14:10
            annotation_type="ai_summary",
            content="AI summary",
        )
        self.db.create_annotation(annotation2)

        self.db.connection.commit()

        # Get annotations for timeline
        annotations_by_timestamp = self.db.get_annotations_for_timeline(
            self.source_id,
            start=datetime(2025, 8, 22, 14, 0, 0),
            end=datetime(2025, 8, 22, 14, 30, 0),
        )

        # Check that annotations are properly mapped to timestamps
        timestamp_14_00 = datetime(2025, 8, 22, 14, 0, 0)
        timestamp_14_10 = datetime(2025, 8, 22, 14, 10, 0)

        self.assertIn(timestamp_14_00, annotations_by_timestamp)
        self.assertEqual(len(annotations_by_timestamp[timestamp_14_00]), 1)
        self.assertEqual(
            annotations_by_timestamp[timestamp_14_00][0].content, "First note"
        )

        self.assertIn(timestamp_14_10, annotations_by_timestamp)
        self.assertEqual(len(annotations_by_timestamp[timestamp_14_10]), 1)
        self.assertEqual(
            annotations_by_timestamp[timestamp_14_10][0].content, "AI summary"
        )


if __name__ == "__main__":
    unittest.main()
