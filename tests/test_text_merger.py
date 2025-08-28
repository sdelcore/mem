"""Tests for the text_merger module."""

import unittest

from src.capture.text_merger import (
    find_overlap,
    merge_overlapping_texts,
    deduplicate_segments,
)


class TestTextMerger(unittest.TestCase):
    """Tests for text merging functions."""

    def test_find_overlap_exact_match(self):
        """Test finding overlap with exact matching text."""
        text1 = "The quick brown fox jumps over the lazy dog"
        text2 = "jumps over the lazy dog and runs away"

        overlap_pos = find_overlap(text1, text2, min_overlap_ratio=0.8)
        self.assertIsNotNone(overlap_pos)
        # Should find where "jumps" starts in text1
        self.assertIn("jumps", text1[overlap_pos:])

    def test_find_overlap_no_match(self):
        """Test when there's no overlap between texts."""
        text1 = "The quick brown fox"
        text2 = "A completely different sentence"

        overlap_pos = find_overlap(text1, text2)
        self.assertIsNone(overlap_pos)

    def test_find_overlap_short_text(self):
        """Test with texts too short to find overlap."""
        text1 = "Hi there"
        text2 = "there friend"

        overlap_pos = find_overlap(text1, text2)
        self.assertIsNone(overlap_pos)  # Too short (< 5 words each)

    def test_merge_overlapping_texts_with_overlap(self):
        """Test merging texts that have overlap."""
        texts = [
            ("The quick brown fox jumps over the lazy dog", 0.9),
            ("jumps over the lazy dog and runs away quickly", 0.95),
        ]

        merged = merge_overlapping_texts(texts)

        # Should contain both parts without duplication
        self.assertIn("quick brown fox", merged)
        self.assertIn("runs away quickly", merged)
        # Should not duplicate the overlapping part
        self.assertEqual(merged.count("jumps over the lazy dog"), 1)

    def test_merge_overlapping_texts_no_overlap(self):
        """Test merging texts without overlap."""
        texts = [
            ("First sentence here.", 0.9),
            ("Second sentence here.", 0.9),
            ("Third sentence here.", 0.9),
        ]

        merged = merge_overlapping_texts(texts)

        # Should contain all three sentences
        self.assertIn("First sentence", merged)
        self.assertIn("Second sentence", merged)
        self.assertIn("Third sentence", merged)

    def test_merge_overlapping_texts_empty(self):
        """Test merging empty list of texts."""
        merged = merge_overlapping_texts([])
        self.assertEqual(merged, "")

    def test_merge_overlapping_texts_single(self):
        """Test merging single text."""
        texts = [("Single text here", 0.9)]
        merged = merge_overlapping_texts(texts)
        self.assertEqual(merged, "Single text here")

    def test_deduplicate_segments_exact_duplicates(self):
        """Test deduplicating exact duplicate segments."""
        segments = [
            {"text": "Hello world", "start": 0.0, "end": 2.0},
            {"text": "Hello world", "start": 1.5, "end": 3.5},
            {"text": "Different text", "start": 4.0, "end": 6.0},
        ]

        deduped = deduplicate_segments(segments)

        # Should merge the duplicate "Hello world" segments
        self.assertEqual(len(deduped), 2)
        # First segment should have extended end time
        self.assertEqual(deduped[0]["text"], "Hello world")
        self.assertEqual(deduped[0]["end"], 3.5)
        # Second segment should remain
        self.assertEqual(deduped[1]["text"], "Different text")

    def test_deduplicate_segments_no_overlap(self):
        """Test segments with no overlap."""
        segments = [
            {"text": "First", "start": 0.0, "end": 2.0},
            {"text": "Second", "start": 3.0, "end": 5.0},
            {"text": "Third", "start": 6.0, "end": 8.0},
        ]

        deduped = deduplicate_segments(segments)

        # No changes expected
        self.assertEqual(len(deduped), 3)
        self.assertEqual(deduped, segments)

    def test_deduplicate_segments_empty(self):
        """Test with empty segment list."""
        deduped = deduplicate_segments([])
        self.assertEqual(deduped, [])

    def test_deduplicate_segments_single(self):
        """Test with single segment."""
        segments = [{"text": "Single", "start": 0.0, "end": 2.0}]
        deduped = deduplicate_segments(segments)
        self.assertEqual(deduped, segments)

    def test_deduplicate_segments_overlapping_different_text(self):
        """Test overlapping segments with different text."""
        segments = [
            {"text": "First part", "start": 0.0, "end": 3.0},
            {"text": "Second part", "start": 2.5, "end": 5.0},  # Small overlap
            {"text": "Third part", "start": 5.5, "end": 8.0},  # No overlap
        ]

        deduped = deduplicate_segments(segments)

        # Should keep all three as they have different text
        self.assertEqual(len(deduped), 3)

    def test_merge_with_confidence_preference(self):
        """Test that higher confidence text is preferred in overlaps."""
        texts = [
            ("The quick brown fox jumps over the lazy dog", 0.7),
            ("jumps over the lazy dog and runs away", 0.95),
        ]

        merged = merge_overlapping_texts(texts)

        # The overlapping part should use the higher confidence version
        self.assertIn("runs away", merged)
        self.assertIn("quick brown fox", merged)
