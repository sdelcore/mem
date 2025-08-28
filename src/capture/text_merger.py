"""Text merging utilities for handling overlapping transcriptions."""

import difflib
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def find_overlap(text1: str, text2: str, min_overlap_ratio: float = 0.8) -> Optional[int]:
    """
    Find the overlap point between two texts.

    Args:
        text1: First text (earlier chunk)
        text2: Second text (later chunk)
        min_overlap_ratio: Minimum similarity ratio to consider as overlap (0-1)

    Returns:
        Index in text1 where overlap starts, or None if no overlap found
    """
    if not text1 or not text2:
        return None

    # Split into words for better matching
    words1 = text1.split()
    words2 = text2.split()

    if len(words1) < 3 or len(words2) < 3:
        # Too short to find meaningful overlap
        return None

    # Try to find where text2 begins in text1
    # Start with longer sequences for better accuracy
    best_match_pos = None
    best_match_length = 0

    # Look for the beginning of text2 at the end of text1
    # Try different starting positions in text1
    for start_idx in range(len(words1) - 2):  # Need at least 3 words
        # How many words from text2 match starting from this position in text1?
        match_length = 0
        for i in range(min(len(words2), len(words1) - start_idx)):
            if words1[start_idx + i].lower() == words2[i].lower():
                match_length += 1
            else:
                break

        # If we found a good match that's better than before
        if match_length >= 3 and match_length > best_match_length:
            # Check if this is a significant match (at least min_overlap_ratio of possible overlap)
            possible_overlap = min(len(words2), len(words1) - start_idx)
            if match_length / possible_overlap >= min_overlap_ratio:
                best_match_length = match_length
                # Calculate character position where this match starts
                if start_idx == 0:
                    best_match_pos = 0
                else:
                    best_match_pos = len(" ".join(words1[:start_idx])) + 1

    if best_match_pos is not None:
        logger.debug(f"Found overlap of {best_match_length} words at position {best_match_pos}")

    return best_match_pos


def merge_overlapping_texts(texts: List[Tuple[str, float]], overlap_threshold: float = 0.8) -> str:
    """
    Merge a list of potentially overlapping text chunks.

    Args:
        texts: List of (text, confidence) tuples in chronological order
        overlap_threshold: Minimum similarity to consider as overlap

    Returns:
        Merged text with overlaps removed
    """
    if not texts:
        return ""

    if len(texts) == 1:
        return texts[0][0]

    merged_parts = []
    current_text, current_confidence = texts[0]

    for next_text, next_confidence in texts[1:]:
        overlap_pos = find_overlap(current_text, next_text, overlap_threshold)

        if overlap_pos is not None:
            # Found overlap - merge the texts
            if overlap_pos > 0:
                # Keep the non-overlapping part of current text
                merged_parts.append(current_text[:overlap_pos].rstrip())

            # Use the higher confidence version for the overlapping part
            overlap_in_current = (
                current_text[overlap_pos:] if overlap_pos < len(current_text) else ""
            )

            # Determine which version to use based on confidence
            if next_confidence > current_confidence:
                # Use the version from next_text (it's already included)
                current_text = next_text
            else:
                # Merge: keep overlap from current, add rest from next
                # Find where overlap ends in next_text
                words_current = overlap_in_current.split()
                words_next = next_text.split()

                # Find common prefix length
                common_len = 0
                for i in range(min(len(words_current), len(words_next))):
                    if words_current[i].lower() == words_next[i].lower():
                        common_len = i + 1
                    else:
                        break

                # Combine the texts
                if common_len > 0:
                    rest_of_next = " ".join(words_next[common_len:])
                    current_text = (
                        overlap_in_current + " " + rest_of_next
                        if rest_of_next
                        else overlap_in_current
                    )
                else:
                    current_text = next_text

            current_confidence = max(current_confidence, next_confidence)
        else:
            # No overlap found - append current and move to next
            merged_parts.append(current_text)
            current_text = next_text
            current_confidence = next_confidence

    # Add the last text
    merged_parts.append(current_text)

    # Join all parts with space
    merged_text = " ".join(merged_parts)

    # Clean up extra whitespace
    merged_text = " ".join(merged_text.split())

    return merged_text


def deduplicate_segments(segments: List[dict]) -> List[dict]:
    """
    Remove duplicate segments from overlapping chunks.

    Args:
        segments: List of segment dictionaries with 'text', 'start', 'end' keys

    Returns:
        Deduplicated list of segments
    """
    if len(segments) <= 1:
        return segments

    # Sort by start time
    sorted_segments = sorted(segments, key=lambda x: x["start"])

    deduplicated = []
    last_segment = None

    for segment in sorted_segments:
        if last_segment is None:
            deduplicated.append(segment)
            last_segment = segment
        else:
            # Check if this segment overlaps with the last one
            if segment["start"] < last_segment["end"]:
                # Overlapping segments - check if they're duplicates
                if segment["text"].strip().lower() == last_segment["text"].strip().lower():
                    # Duplicate - extend the last segment's end time if needed
                    last_segment["end"] = max(last_segment["end"], segment["end"])
                else:
                    # Different text but overlapping time - keep both but adjust times
                    if segment["start"] < last_segment["end"] - 0.5:  # Significant overlap
                        # Likely the same content, keep the one with better timing
                        if len(segment["text"]) > len(last_segment["text"]):
                            deduplicated[-1] = segment
                            last_segment = segment
                    else:
                        deduplicated.append(segment)
                        last_segment = segment
            else:
                # No overlap
                deduplicated.append(segment)
                last_segment = segment

    return deduplicated
