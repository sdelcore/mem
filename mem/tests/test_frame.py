"""Tests for frame processing module."""

import pytest
from io import BytesIO
from PIL import Image

from src.capture.frame import FrameProcessor


@pytest.fixture
def frame_processor():
    return FrameProcessor(similarity_threshold=95.0)


def create_test_image(pattern="solid", color=(255, 0, 0), size=(100, 100)):
    """Create a test image with specified pattern."""
    img = Image.new("RGB", size, color)

    if pattern == "gradient":
        for x in range(size[0]):
            for y in range(size[1]):
                r = int(color[0] * (x / size[0]))
                g = int(color[1] * (x / size[0]))
                b = int(color[2] * (x / size[0]))
                img.putpixel((x, y), (r, g, b))
    elif pattern == "checkerboard":
        for x in range(size[0]):
            for y in range(size[1]):
                if (x // 10 + y // 10) % 2:
                    img.putpixel((x, y), color)
                else:
                    img.putpixel((x, y), (0, 0, 0))
    elif pattern == "noise":
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


class TestFrameProcessor:
    def test_calculate_hash(self, frame_processor):
        image_bytes = create_test_image(color=(255, 0, 0))
        hash_value = frame_processor.calculate_hash(image_bytes)

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # 16x16 dhash = 256 bits = 64 hex chars

    def test_calculate_similarity_identical(self, frame_processor):
        image_bytes = create_test_image(color=(255, 0, 0))
        hash1 = frame_processor.calculate_hash(image_bytes)
        hash2 = frame_processor.calculate_hash(image_bytes)

        similarity = frame_processor.calculate_similarity(hash1, hash2)
        assert similarity == 100.0

    def test_calculate_similarity_different(self, frame_processor):
        image1 = create_test_image(pattern="gradient", color=(255, 0, 0))
        image2 = create_test_image(pattern="noise", color=(0, 0, 255))

        hash1 = frame_processor.calculate_hash(image1)
        hash2 = frame_processor.calculate_hash(image2)

        similarity = frame_processor.calculate_similarity(hash1, hash2)
        assert similarity < 95.0

    def test_should_store_first_frame(self, frame_processor):
        source_id = 1
        image_bytes = create_test_image()

        should_store, phash, similarity = frame_processor.should_store_frame(
            source_id, image_bytes
        )

        assert should_store
        assert isinstance(phash, str)
        assert similarity == 0.0

    def test_should_store_duplicate_frame(self, frame_processor):
        source_id = 1
        image_bytes = create_test_image(color=(100, 100, 100))

        # First frame
        should_store1, phash1, _ = frame_processor.should_store_frame(
            source_id, image_bytes
        )
        assert should_store1

        # Same frame again
        should_store2, phash2, sim2 = frame_processor.should_store_frame(
            source_id, image_bytes
        )
        assert not should_store2
        assert phash1 == phash2
        assert sim2 >= 95.0

    def test_should_store_different_frame(self, frame_processor):
        source_id = 1

        # First frame
        image1 = create_test_image(pattern="gradient", color=(255, 0, 0))
        should_store1, _, _ = frame_processor.should_store_frame(source_id, image1)
        assert should_store1

        # Different frame
        image2 = create_test_image(pattern="checkerboard", color=(0, 255, 0))
        should_store2, _, sim2 = frame_processor.should_store_frame(source_id, image2)
        assert should_store2
        assert sim2 < 95.0

    def test_multiple_sources(self, frame_processor):
        image_bytes = create_test_image()

        # First frame for source 1
        should_store1, _, _ = frame_processor.should_store_frame(1, image_bytes)
        assert should_store1

        # Same frame for source 1 (duplicate)
        should_store2, _, _ = frame_processor.should_store_frame(1, image_bytes)
        assert not should_store2

        # Same frame for source 2 (first for this source)
        should_store3, _, _ = frame_processor.should_store_frame(2, image_bytes)
        assert should_store3

    def test_reset_source(self, frame_processor):
        source_id = 1
        image_bytes = create_test_image()

        # Store first frame
        frame_processor.should_store_frame(source_id, image_bytes)

        # Reset source
        frame_processor.reset_source(source_id)

        # Same frame should now be stored as first
        should_store, _, similarity = frame_processor.should_store_frame(
            source_id, image_bytes
        )
        assert should_store
        assert similarity == 0.0

    def test_similarity_threshold(self):
        dedup = FrameProcessor(similarity_threshold=80.0)
        source_id = 1

        img1 = Image.new("RGB", (100, 100), (100, 100, 100))
        img2 = Image.new("RGB", (100, 100), (110, 110, 110))

        buffer1 = BytesIO()
        img1.save(buffer1, format="JPEG", quality=85)
        buffer2 = BytesIO()
        img2.save(buffer2, format="JPEG", quality=85)

        # Store first frame
        dedup.should_store_frame(source_id, buffer1.getvalue())

        # Check if slightly different frame is stored
        should_store, _, similarity = dedup.should_store_frame(
            source_id, buffer2.getvalue()
        )

        if similarity >= 80.0:
            assert not should_store
        else:
            assert should_store

    def test_get_stats(self, frame_processor):
        frame_processor.should_store_frame(1, create_test_image())
        frame_processor.should_store_frame(2, create_test_image())

        stats = frame_processor.get_stats()

        assert stats["sources_tracked"] == 2
        assert stats["similarity_threshold"] == 95.0
