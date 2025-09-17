"""RTMP streaming server for OBS Studio integration."""

import asyncio
import json
import logging
import subprocess
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Dict, Optional

from src.capture.pipeline import StreamCaptureProcessor
from src.config import config

logger = logging.getLogger(__name__)


@dataclass
class StreamSession:
    """Represents an active streaming session."""

    session_id: str
    stream_key: str
    stream_name: Optional[str] = None
    source_id: Optional[int] = None
    processor: Optional[StreamCaptureProcessor] = None
    process: Optional[subprocess.Popen] = None
    status: str = "waiting"  # waiting, live, ended, error
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    bitrate: Optional[int] = None
    frames_received: int = 0
    frames_stored: int = 0


class RTMPServer:
    """Manages RTMP server for receiving streams from OBS Studio."""

    def __init__(self, port: int = 1935, max_streams: int = 10):
        """
        Initialize RTMP server.

        Args:
            port: RTMP server port (default 1935)
            max_streams: Maximum concurrent streams
        """
        self.port = port
        self.max_streams = max_streams
        self.sessions: Dict[str, StreamSession] = {}
        self.active = False
        self.frame_queue = Queue()
        self.worker_thread = None

    def generate_stream_key(self) -> str:
        """Generate a unique stream key."""
        return str(uuid.uuid4())

    def create_session(self, stream_name: str = None) -> StreamSession:
        """
        Create a new streaming session.

        Args:
            stream_name: Optional name for the stream

        Returns:
            New StreamSession object
        """
        if len(self.sessions) >= self.max_streams:
            raise RuntimeError(f"Maximum streams ({self.max_streams}) reached")

        session_id = str(uuid.uuid4())
        stream_key = self.generate_stream_key()

        session = StreamSession(
            session_id=session_id,
            stream_key=stream_key,
            stream_name=stream_name,
            status="waiting",
        )

        self.sessions[stream_key] = session
        logger.info(
            f"Created stream session {session_id} with key {stream_key} and name '{stream_name}'"
        )

        return session

    def start_stream(self, stream_key: str) -> bool:
        """
        Start receiving stream for a session.

        Args:
            stream_key: Stream key to start

        Returns:
            True if started successfully
        """
        session = self.sessions.get(stream_key)
        if not session:
            logger.error(f"Stream key {stream_key} not found")
            return False

        if session.status != "waiting":
            logger.warning(
                f"Stream {stream_key} not in waiting state: {session.status}"
            )
            return False

        try:
            # Initialize stream processor
            session.processor = StreamCaptureProcessor()
            session.source_id = session.processor.start_stream(stream_type="rtmp")

            # Start FFmpeg process to receive RTMP stream
            # Output frames as JPEG at specified interval
            ffmpeg_cmd = [
                "ffmpeg",
                "-listen",
                "1",  # Act as server
                "-i",
                f"rtmp://localhost:{self.port}/live/{stream_key}",
                "-f",
                "image2pipe",  # Output as image pipe
                "-vcodec",
                "mjpeg",  # Output JPEG frames
                "-r",
                "1",  # 1 frame per second (configurable)
                "-q:v",
                "2",  # High quality JPEG
                "-",  # Output to stdout
            ]

            session.process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8,
            )

            session.status = "live"
            session.started_at = datetime.now()

            # Start frame processing thread
            thread = threading.Thread(
                target=self._process_stream_frames, args=(session,)
            )
            thread.daemon = True
            thread.start()

            logger.info(f"Started RTMP stream reception for {stream_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to start stream {stream_key}: {e}")
            session.status = "error"
            if session.processor:
                session.processor.stop_stream()
            return False

    def _process_stream_frames(self, session: StreamSession):
        """
        Process frames from FFmpeg output.

        Args:
            session: StreamSession to process
        """
        jpeg_buffer = bytearray()
        jpeg_start = b"\xff\xd8"  # JPEG start marker
        jpeg_end = b"\xff\xd9"  # JPEG end marker
        in_jpeg = False

        try:
            while session.status == "live" and session.process:
                chunk = session.process.stdout.read(4096)
                if not chunk:
                    break

                # Parse JPEG frames from stream
                for i in range(len(chunk)):
                    if not in_jpeg:
                        # Look for JPEG start
                        if chunk[i : i + 2] == jpeg_start:
                            jpeg_buffer = bytearray(chunk[i:])
                            in_jpeg = True
                    else:
                        jpeg_buffer.append(chunk[i])
                        # Look for JPEG end
                        if chunk[i - 1 : i + 1] == jpeg_end:
                            # Complete JPEG frame found
                            frame_data = bytes(jpeg_buffer)
                            session.frames_received += 1

                            # Process frame (with auto dimension detection)
                            try:
                                session.processor.capture_frame(frame_data)
                                session.frames_stored += 1

                                # Extract dimensions on first frame
                                if session.width is None:
                                    from PIL import Image
                                    from io import BytesIO

                                    img = Image.open(BytesIO(frame_data))
                                    session.width, session.height = img.size
                                    logger.info(
                                        f"Stream {session.stream_key} resolution: "
                                        f"{session.width}x{session.height}"
                                    )

                            except Exception as e:
                                logger.error(f"Failed to process frame: {e}")

                            jpeg_buffer.clear()
                            in_jpeg = False

        except Exception as e:
            logger.error(f"Stream processing error: {e}")
            session.status = "error"

        finally:
            # Clean up
            if session.processor:
                session.processor.stop_stream()
            session.status = "ended"
            session.ended_at = datetime.now()
            logger.info(
                f"Stream {session.stream_key} ended. "
                f"Frames: {session.frames_received} received, {session.frames_stored} stored"
            )

    def stop_stream(self, stream_key: str) -> bool:
        """
        Stop an active stream.

        Args:
            stream_key: Stream key to stop

        Returns:
            True if stopped successfully
        """
        session = self.sessions.get(stream_key)
        if not session:
            return False

        if session.status == "live":
            # Terminate FFmpeg process
            if session.process:
                session.process.terminate()
                session.process.wait(timeout=5)

            # Stop processor
            if session.processor:
                session.processor.stop_stream()

            session.status = "ended"
            session.ended_at = datetime.now()
            logger.info(f"Stopped stream {stream_key}")

        return True

    def get_session(self, stream_key: str) -> Optional[StreamSession]:
        """Get session by stream key."""
        return self.sessions.get(stream_key)

    def get_all_sessions(self) -> list[StreamSession]:
        """Get all sessions."""
        return list(self.sessions.values())

    def delete_session(self, stream_key: str) -> bool:
        """
        Delete a session.

        Args:
            stream_key: Stream key to delete

        Returns:
            True if deleted
        """
        if stream_key in self.sessions:
            # Stop if still running
            self.stop_stream(stream_key)
            del self.sessions[stream_key]
            return True
        return False

    def get_stream_url(self, stream_key: str) -> str:
        """
        Get RTMP URL for OBS configuration.

        Args:
            stream_key: Stream key

        Returns:
            RTMP URL string
        """
        return f"rtmp://localhost:{self.port}/live/{stream_key}"

    def get_status(self) -> dict:
        """Get server status and statistics."""
        active_streams = sum(1 for s in self.sessions.values() if s.status == "live")

        return {
            "server": {
                "active": self.active,
                "port": self.port,
                "max_streams": self.max_streams,
            },
            "streams": {
                "active": active_streams,
                "total": len(self.sessions),
                "sessions": [
                    {
                        "session_id": s.session_id,
                        "stream_key": s.stream_key,
                        "status": s.status,
                        "resolution": f"{s.width}x{s.height}" if s.width else None,
                        "frames_received": s.frames_received,
                        "frames_stored": s.frames_stored,
                        "started_at": (
                            s.started_at.isoformat() if s.started_at else None
                        ),
                        "duration": (
                            (datetime.now() - s.started_at).total_seconds()
                            if s.started_at and s.status == "live"
                            else None
                        ),
                    }
                    for s in self.sessions.values()
                ],
            },
        }
