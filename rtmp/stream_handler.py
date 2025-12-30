#!/usr/bin/env python3
"""
RTMP Stream Handler

Handles frame extraction from RTMP streams and sends them to the backend.
This script is called by nginx-rtmp's exec_push directive when a stream starts.

Usage:
    stream_handler.py extract_frames <stream_key>

The script will:
1. Connect to the local RTMP stream using FFmpeg
2. Extract JPEG frames at the configured interval (default 1fps)
3. POST each frame to the backend's frame ingestion endpoint
4. Continue until the stream ends or an error occurs
"""

import os
import subprocess
import sys
import time

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://mem-backend:8000")
# Frame extraction rate - should match streaming.capture.frame_interval_seconds config
FRAME_INTERVAL = int(os.environ.get("FRAME_INTERVAL", "1"))


def log(message: str, level: str = "INFO"):
    """Log message to stderr (nginx captures this)."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] stream_handler: {message}", file=sys.stderr)


def post_frame(stream_key: str, frame_data: bytes) -> bool:
    """POST a frame to the backend frame ingestion endpoint."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{BACKEND_URL}/api/streams/{stream_key}/frame",
                files={"file": ("frame.jpg", frame_data, "image/jpeg")},
            )
            if response.status_code != 200:
                log(f"Failed to post frame: HTTP {response.status_code}", "WARNING")
                return False
            return True
    except httpx.TimeoutException:
        log(f"Timeout posting frame for stream {stream_key}", "WARNING")
        return False
    except httpx.ConnectError as e:
        log(f"Connection error posting frame: {e}", "WARNING")
        return False
    except Exception as e:
        log(f"Error posting frame: {e}", "WARNING")
        return False


def extract_frames(stream_key: str):
    """
    Extract frames from RTMP stream and POST to backend.

    Uses FFmpeg to read from the local nginx-rtmp stream and output
    JPEG frames to stdout at the configured frame rate.
    """
    rtmp_url = f"rtmp://localhost/live/{stream_key}"
    log(f"Starting frame extraction for stream {stream_key} at {FRAME_INTERVAL}fps")

    # FFmpeg command to extract JPEG frames from RTMP stream
    # -re: Read input at native frame rate (important for live streams)
    # -i: Input URL (the local RTMP stream)
    # -f image2pipe: Output format as pipe of images
    # -vcodec mjpeg: Output codec as Motion JPEG
    # -r: Output frame rate
    # -q:v 2: JPEG quality (2 = high quality, range 2-31)
    # -: Output to stdout
    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel", "warning",
        "-re",
        "-i", rtmp_url,
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "-r", str(FRAME_INTERVAL),
        "-q:v", "2",
        "-",
    ]

    log(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")

    try:
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8,  # Large buffer for frame data
        )
    except Exception as e:
        log(f"Failed to start FFmpeg: {e}", "ERROR")
        return

    # JPEG markers for frame detection
    jpeg_start = b"\xff\xd8"  # Start of Image marker
    jpeg_end = b"\xff\xd9"    # End of Image marker

    jpeg_buffer = bytearray()
    in_jpeg = False
    frame_count = 0
    success_count = 0
    fail_count = 0

    log("Waiting for frames from FFmpeg...")

    try:
        while True:
            # Read chunks from FFmpeg stdout
            chunk = process.stdout.read(4096)
            if not chunk:
                # Check if FFmpeg has exited
                if process.poll() is not None:
                    log(f"FFmpeg process exited with code {process.returncode}")
                    break
                continue

            # Parse JPEG frames from the stream
            i = 0
            while i < len(chunk):
                if not in_jpeg:
                    # Look for JPEG start marker
                    if i + 1 < len(chunk) and chunk[i:i + 2] == jpeg_start:
                        jpeg_buffer = bytearray(chunk[i:])
                        in_jpeg = True
                        i = len(chunk)  # Consumed rest of chunk
                    else:
                        i += 1
                else:
                    jpeg_buffer.append(chunk[i])
                    # Look for JPEG end marker
                    if len(jpeg_buffer) >= 2 and jpeg_buffer[-2:] == jpeg_end:
                        # Complete JPEG frame found
                        frame_data = bytes(jpeg_buffer)
                        frame_count += 1

                        # POST frame to backend
                        if post_frame(stream_key, frame_data):
                            success_count += 1
                        else:
                            fail_count += 1

                        # Log progress every 60 frames (~1 minute at 1fps)
                        if frame_count % 60 == 0:
                            log(
                                f"Stream {stream_key}: {frame_count} frames extracted, "
                                f"{success_count} sent, {fail_count} failed"
                            )

                        jpeg_buffer.clear()
                        in_jpeg = False
                    i += 1

    except KeyboardInterrupt:
        log("Interrupted by user")
    except Exception as e:
        log(f"Error during frame extraction: {e}", "ERROR")
    finally:
        # Clean up FFmpeg process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        log(
            f"Frame extraction ended for stream {stream_key}. "
            f"Total: {frame_count} frames, {success_count} sent, {fail_count} failed"
        )


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: stream_handler.py <command> <stream_key>", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  extract_frames  - Extract frames from RTMP and send to backend", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    stream_key = sys.argv[2]

    if command == "extract_frames":
        extract_frames(stream_key)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
