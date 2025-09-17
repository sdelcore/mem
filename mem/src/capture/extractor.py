"""Frame extraction and timestamp parsing for video files."""

import logging
import re
from collections.abc import Generator
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from src.config import config

logger = logging.getLogger(__name__)


def parse_video_timestamp(filename: str) -> datetime:
    """
    Parse timestamp from filename format: YYYY-MM-DD_HH-MM-SS.mp4

    Args:
        filename: Video filename in format YYYY-MM-DD_HH-MM-SS.mp4

    Returns:
        Local datetime parsed from filename

    Raises:
        ValueError: If filename doesn't match expected format
    """
    # Remove extension
    stem = Path(filename).stem

    # Expected format from config
    pattern = config.files.filename_regex
    match = re.match(pattern, stem)

    if not match:
        raise ValueError(
            f"Invalid filename format: {filename}. "
            f"Expected: {config.files.filename_format}.mp4"
        )

    year, month, day, hour, minute, second = map(int, match.groups())

    # Create datetime in local timezone
    return datetime(year, month, day, hour, minute, second)


def get_video_duration(video_path: Path) -> float:
    """
    Get the duration of a video in seconds.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds
    """
    cap = cv2.VideoCapture(str(video_path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps if fps > 0 else 0
        return duration
    finally:
        cap.release()


def get_video_info(video_path: Path) -> dict:
    """
    Get video metadata.

    Args:
        video_path: Path to video file

    Returns:
        Dictionary with video metadata
    """
    cap = cv2.VideoCapture(str(video_path))
    try:
        info = {
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "duration": get_video_duration(video_path),
            "codec": cap.get(cv2.CAP_PROP_FOURCC),
        }
        return info
    finally:
        cap.release()


def frame_to_jpeg(frame: np.ndarray, quality: int = None) -> bytes:
    """
    Convert a frame to JPEG bytes.

    Args:
        frame: OpenCV frame (BGR format)
        quality: JPEG quality (1-100, uses config default if None)

    Returns:
        JPEG bytes
    """
    if quality is None:
        quality = config.capture.frame.jpeg_quality

    # Convert BGR to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Convert to PIL Image
    img = Image.fromarray(rgb_frame)

    # Save to bytes
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def extract_frames(
    video_path: Path, interval: int = None, quality: int = None
) -> Generator[tuple[float, bytes], None, None]:
    """
    Extract frames from video at specified intervals.

    Args:
        video_path: Path to video file
        interval: Seconds between frame extraction (uses config default if None)
        quality: JPEG quality (1-100, uses config default if None)

    Yields:
        Tuple of (timestamp_seconds, frame_jpeg_bytes)
    """
    if interval is None:
        interval = config.capture.frame.interval_seconds
    if quality is None:
        quality = config.capture.frame.jpeg_quality

    cap = cv2.VideoCapture(str(video_path))

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps <= 0:
            logger.error(f"Invalid FPS for video: {video_path}")
            return

        frame_interval = int(fps * interval)

        # Use seeking instead of reading all frames
        frame_number = 0
        while frame_number < total_frames:
            # Seek to the target frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

            ret, frame = cap.read()
            if not ret:
                break

            timestamp_seconds = frame_number / fps
            jpeg_bytes = frame_to_jpeg(frame, quality)

            logger.debug(f"Extracted frame at {timestamp_seconds:.1f}s")
            yield timestamp_seconds, jpeg_bytes

            # Jump to next target frame
            frame_number += frame_interval

    finally:
        cap.release()


def extract_audio(video_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Extract audio from video file.

    Args:
        video_path: Path to video file
        output_path: Optional output path for audio file

    Returns:
        Path to extracted audio file
    """
    import subprocess

    if output_path is None:
        output_path = video_path.with_suffix(".wav")

    cmd = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-vn",  # No video
        "-acodec",
        "pcm_s16le",  # PCM 16-bit
        "-ar",
        "16000",  # 16kHz sample rate for Whisper
        "-ac",
        "1",  # Mono
        "-y",  # Overwrite output
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Failed to extract audio: {result.stderr}")
        raise RuntimeError(f"Audio extraction failed: {result.stderr}")

    return output_path


def get_audio_chunks(
    audio_path: Path, chunk_duration: int = None, overlap_seconds: int = None
) -> Generator[dict, None, None]:
    """
    Split audio into chunks for processing with optional overlap.

    Args:
        audio_path: Path to audio file
        chunk_duration: Duration of each chunk in seconds (uses config default if None)
        overlap_seconds: Overlap between chunks in seconds (uses config default if None)

    Yields:
        Dictionary with chunk information including overlap metadata
    """
    if chunk_duration is None:
        chunk_duration = config.capture.audio.chunk_duration_seconds
    if overlap_seconds is None:
        overlap_seconds = getattr(config.capture.audio, "overlap_seconds", 0)

    import wave

    with wave.open(str(audio_path), "rb") as wav:
        sample_rate = wav.getframerate()
        total_frames = wav.getnframes()
        chunk_frames = int(sample_rate * chunk_duration)
        overlap_frames = int(sample_rate * overlap_seconds)

        # Calculate step size (how much to advance between chunks)
        step_frames = chunk_frames - overlap_frames
        if step_frames <= 0:
            step_frames = chunk_frames  # Fallback if overlap is too large

        start_frame = 0
        chunk_index = 0

        while start_frame < total_frames:
            # Calculate actual chunk boundaries
            end_frame = min(start_frame + chunk_frames, total_frames)

            # Read chunk
            wav.setpos(start_frame)
            frames = wav.readframes(end_frame - start_frame)

            # Calculate overlap boundaries for this chunk
            has_overlap_before = chunk_index > 0 and overlap_seconds > 0
            has_overlap_after = end_frame < total_frames and overlap_seconds > 0

            overlap_start = None
            overlap_end = None

            if has_overlap_before:
                # This chunk overlaps with the previous one
                overlap_start = start_frame / sample_rate

            if has_overlap_after:
                # This chunk will overlap with the next one
                overlap_end = (end_frame - overlap_frames) / sample_rate

            yield {
                "index": chunk_index,
                "start_seconds": start_frame / sample_rate,
                "end_seconds": end_frame / sample_rate,
                "audio_data": frames,
                "sample_rate": sample_rate,
                "has_overlap": has_overlap_before or has_overlap_after,
                "overlap_start_seconds": overlap_start,
                "overlap_end_seconds": overlap_end,
            }

            # Move to next chunk start position (with overlap)
            start_frame += step_frames
            chunk_index += 1
