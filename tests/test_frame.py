"""Tests for frame processing module."""

import unittest
from io import BytesIO
from PIL import Image
import numpy as np

from src.capture.frame import FrameProcessor


class TestFrameProcessor(unittest.TestCase):
    """Test frame processing functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.frame_processor = FrameProcessor(similarity_threshold=95.0)

    def create_test_image(self, pattern="solid", color=(255, 0, 0), size=(100, 100)):
        """
        Create a test image with specified pattern.

        Args:
            pattern: Type of pattern ("solid", "gradient", "checkerboard", "noise")
            color: Base RGB color tuple
            size: Image dimensions (width, height)

        Returns:
            JPEG bytes of the test image
        """
        img = Image.new("RGB", size, color)

        if pattern == "gradient":
            # Create horizontal gradient
            for x in range(size[0]):
                for y in range(size[1]):
                    r = int(color[0] * (x / size[0]))
                    g = int(color[1] * (x / size[0]))
                    b = int(color[2] * (x / size[0]))
                    img.putpixel((x, y), (r, g, b))
        elif pattern == "checkerboard":
            # Create checkerboard pattern
            for x in range(size[0]):
                for y in range(size[1]):
                    if (x // 10 + y // 10) % 2:
                        img.putpixel((x, y), color)
                    else:
                        img.putpixel((x, y), (0, 0, 0))
        elif pattern == "noise":
            # Add random noise to base color
            import random

            for x in range(size[0]):
                for y in range(size[1]):
                    r = min(255, max(0, color[0] + random.randint(-30, 30)))
                    g = min(255, max(0, color[1] + random.randint(-30, 30)))
                    b = min(255, max(0, color[2] + random.randint(-30, 30)))
                    img.putpixel((x, y), (r, g, b))

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()

    def test_calculate_hash(self):
        """Test perceptual hash calculation."""
        image_bytes = self.create_test_image(color=(255, 0, 0))
        hash_value = self.frame_processor.calculate_hash(image_bytes)

        # Hash should be a string
        self.assertIsInstance(hash_value, str)
        # Hash should have expected length (16x16 dhash = 256 bits = 64 hex chars)
        self.assertEqual(len(hash_value), 64)

    def test_calculate_similarity_identical(self):
        """Test similarity calculation for identical images."""
        image_bytes = self.create_test_image(color=(255, 0, 0))
        hash1 = self.frame_processor.calculate_hash(image_bytes)
        hash2 = self.frame_processor.calculate_hash(image_bytes)

        similarity = self.frame_processor.calculate_similarity(hash1, hash2)
        # Identical images should have 100% similarity
        self.assertEqual(similarity, 100.0)

    def test_calculate_similarity_different(self):
        """Test similarity calculation for different images."""
        image1 = self.create_test_image(pattern="gradient", color=(255, 0, 0))  # Red gradient
        image2 = self.create_test_image(
            pattern="noise", color=(0, 0, 255)
        )  # Blue noise - very different

        hash1 = self.frame_processor.calculate_hash(image1)
        hash2 = self.frame_processor.calculate_hash(image2)

        similarity = self.frame_processor.calculate_similarity(hash1, hash2)
        # Different pattern images should have lower similarity than threshold
        self.assertLess(similarity, 95.0)  # Below our 95% threshold

    def test_should_store_first_frame(self):
        """Test that first frame for a source is always stored."""
        source_id = 1
        image_bytes = self.create_test_image()

        should_store, phash, similarity = self.frame_processor.should_store_frame(
            source_id, image_bytes
        )

        self.assertTrue(should_store)
        self.assertIsInstance(phash, str)
        self.assertEqual(similarity, 0.0)  # First frame has no previous to compare

    def test_should_store_duplicate_frame(self):
        """Test that duplicate frames are not stored."""
        source_id = 1
        image_bytes = self.create_test_image(color=(100, 100, 100))

        # First frame
        should_store1, phash1, sim1 = self.frame_processor.should_store_frame(
            source_id, image_bytes
        )
        self.assertTrue(should_store1)

        # Same frame again
        should_store2, phash2, sim2 = self.frame_processor.should_store_frame(
            source_id, image_bytes
        )
        self.assertFalse(should_store2)  # Should not store duplicate
        self.assertEqual(phash1, phash2)  # Same hash
        self.assertGreaterEqual(sim2, 95.0)  # High similarity

    def test_should_store_different_frame(self):
        """Test that different frames are stored."""
        source_id = 1

        # First frame
        image1 = self.create_test_image(pattern="gradient", color=(255, 0, 0))
        should_store1, _, _ = self.frame_processor.should_store_frame(source_id, image1)
        self.assertTrue(should_store1)

        # Different frame
        image2 = self.create_test_image(pattern="checkerboard", color=(0, 255, 0))
        should_store2, _, sim2 = self.frame_processor.should_store_frame(source_id, image2)
        self.assertTrue(should_store2)  # Should store different frame
        self.assertLess(sim2, 95.0)  # Low similarity

    def test_multiple_sources(self):
        """Test that deduplication tracks sources independently."""
        image_bytes = self.create_test_image()

        # First frame for source 1
        should_store1, _, _ = self.frame_processor.should_store_frame(1, image_bytes)
        self.assertTrue(should_store1)

        # Same frame for source 1 (duplicate)
        should_store2, _, _ = self.frame_processor.should_store_frame(1, image_bytes)
        self.assertFalse(should_store2)

        # Same frame for source 2 (first for this source)
        should_store3, _, _ = self.frame_processor.should_store_frame(2, image_bytes)
        self.assertTrue(should_store3)  # Should store as it's first for source 2

    def test_reset_source(self):
        """Test resetting deduplication state for a source."""
        source_id = 1
        image_bytes = self.create_test_image()

        # Store first frame
        self.frame_processor.should_store_frame(source_id, image_bytes)

        # Reset source
        self.frame_processor.reset_source(source_id)

        # Same frame should now be stored as first
        should_store, _, similarity = self.frame_processor.should_store_frame(
            source_id, image_bytes
        )
        self.assertTrue(should_store)
        self.assertEqual(similarity, 0.0)

    def test_similarity_threshold(self):
        """Test custom similarity threshold."""
        # Create frame processor with lower threshold
        dedup = FrameProcessor(similarity_threshold=80.0)

        source_id = 1

        # Create slightly different images
        img1 = Image.new("RGB", (100, 100), (100, 100, 100))
        img2 = Image.new("RGB", (100, 100), (110, 110, 110))  # Slightly lighter

        buffer1 = BytesIO()
        img1.save(buffer1, format="JPEG", quality=85)
        buffer2 = BytesIO()
        img2.save(buffer2, format="JPEG", quality=85)

        # Store first frame
        dedup.should_store_frame(source_id, buffer1.getvalue())

        # Check if slightly different frame is stored
        should_store, _, similarity = dedup.should_store_frame(source_id, buffer2.getvalue())

        # With lower threshold, similar frames might not be stored
        if similarity >= 80.0:
            self.assertFalse(should_store)
        else:
            self.assertTrue(should_store)

    def test_get_stats(self):
        """Test getting deduplication statistics."""
        # Process frames for multiple sources
        self.frame_processor.should_store_frame(1, self.create_test_image())
        self.frame_processor.should_store_frame(2, self.create_test_image())

        stats = self.frame_processor.get_stats()

        self.assertEqual(stats["sources_tracked"], 2)
        self.assertEqual(stats["similarity_threshold"], 95.0)


if __name__ == "__main__":
    unittest.main()
