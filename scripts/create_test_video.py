#!/usr/bin/env python3
"""Create a test video with the correct filename format for testing."""

import cv2
import numpy as np
from datetime import datetime
from pathlib import Path


def create_test_video(output_dir: Path = Path(".")):
    """Create a simple test video with correct naming format."""

    # Create filename with required format
    timestamp = datetime.utcnow()
    filename = timestamp.strftime("%Y-%m-%d_%H-%M-%S.mp4")
    output_path = output_dir / filename

    # Video settings
    width, height = 640, 480
    fps = 30
    duration = 10  # seconds
    total_frames = fps * duration

    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    # Generate frames
    for i in range(total_frames):
        # Create a frame with changing colors
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Add some visual content
        color = (int(255 * (i / total_frames)), 100, 200)
        cv2.rectangle(frame, (50, 50), (width - 50, height - 50), color, -1)

        # Add text
        text = f"Frame {i+1}/{total_frames}"
        cv2.putText(frame, text, (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Add timestamp
        current_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame, current_time, (100, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
        )

        out.write(frame)

    out.release()

    print(f"Created test video: {output_path}")
    print(f"  Duration: {duration} seconds")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps}")
    print(f"  Total frames: {total_frames}")

    return output_path


if __name__ == "__main__":
    output_dir = Path("data/test_videos")
    output_dir.mkdir(parents=True, exist_ok=True)
    create_test_video(output_dir)
