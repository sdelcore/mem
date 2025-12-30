"""RTMP streaming server for OBS Studio integration.

This module manages stream sessions and handles callbacks from nginx-rtmp.
The actual RTMP ingestion is done by nginx-rtmp container, which notifies
this backend via HTTP callbacks when streams start/stop.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Dict, Optional

from PIL import Image

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
    status: str = "waiting"  # waiting, live, ended, error
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    client_addr: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    bitrate: Optional[int] = None
    frames_received: int = 0
    frames_stored: int = 0


class RTMPServer:
    """Manages RTMP server sessions for receiving streams from OBS Studio.
    
    This class handles stream session lifecycle. The actual RTMP server
    is nginx-rtmp which calls back to this backend for:
    - on_publish: When OBS starts streaming (validates stream key)
    - on_publish_done: When OBS stops streaming
    - frame ingestion: Receives frames extracted by nginx's exec_push
    """

    def __init__(self, port: int = 1935, max_streams: int = 10):
        """
        Initialize RTMP server manager.

        Args:
            port: RTMP server port (default 1935)
            max_streams: Maximum concurrent streams
        """
        self.port = port
        self.max_streams = max_streams
        self.sessions: Dict[str, StreamSession] = {}

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

    def on_publish(self, stream_key: str, client_addr: str = "") -> bool:
        """
        Handle nginx-rtmp on_publish callback when OBS starts streaming.

        This validates the stream key and initializes the stream processor.

        Args:
            stream_key: The stream key from OBS
            client_addr: Client IP address

        Returns:
            True if stream key is valid and stream started, False to reject
        """
        session = self.sessions.get(stream_key)
        if not session:
            logger.warning(f"on_publish: Unknown stream key {stream_key} from {client_addr}")
            return False

        if session.status not in ("waiting",):
            logger.warning(
                f"on_publish: Stream {stream_key} in unexpected state '{session.status}'"
            )
            # Allow reconnection if stream ended
            if session.status == "ended":
                logger.info(f"Allowing reconnection for ended stream {stream_key}")
            else:
                return False

        try:
            # Initialize stream processor
            session.processor = StreamCaptureProcessor()
            session.source_id = session.processor.start_stream(stream_type="rtmp")
            session.status = "live"
            session.started_at = datetime.now()
            session.client_addr = client_addr
            session.frames_received = 0
            session.frames_stored = 0
            session.width = None
            session.height = None

            logger.info(
                f"Stream {stream_key} is now live from {client_addr}, source_id={session.source_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start stream {stream_key}: {e}")
            session.status = "error"
            return False

    def on_publish_done(self, stream_key: str) -> bool:
        """
        Handle nginx-rtmp on_publish_done callback when OBS stops streaming.

        Args:
            stream_key: The stream key

        Returns:
            True if handled successfully
        """
        session = self.sessions.get(stream_key)
        if not session:
            logger.warning(f"on_publish_done: Unknown stream key {stream_key}")
            return False

        if session.processor:
            try:
                session.processor.stop_stream()
            except Exception as e:
                logger.error(f"Error stopping processor for {stream_key}: {e}")

        session.status = "ended"
        session.ended_at = datetime.now()
        session.processor = None

        logger.info(
            f"Stream {stream_key} ended. "
            f"Frames: {session.frames_received} received, {session.frames_stored} stored"
        )
        return True

    def ingest_frame(self, stream_key: str, frame_data: bytes) -> bool:
        """
        Ingest a frame from nginx exec_push.

        This is called by the frame ingestion endpoint when nginx's
        stream_handler.py POSTs extracted frames.

        Args:
            stream_key: The stream key
            frame_data: JPEG frame data

        Returns:
            True if frame was processed successfully
        """
        session = self.sessions.get(stream_key)
        if not session:
            logger.warning(f"ingest_frame: Unknown stream key {stream_key}")
            return False

        if session.status != "live":
            logger.warning(
                f"ingest_frame: Stream {stream_key} not live (status={session.status})"
            )
            return False

        if not session.processor:
            logger.error(f"ingest_frame: No processor for stream {stream_key}")
            return False

        try:
            session.frames_received += 1

            # Process frame with deduplication
            session.processor.capture_frame(frame_data)
            session.frames_stored += 1

            # Extract dimensions on first frame
            if session.width is None:
                try:
                    img = Image.open(BytesIO(frame_data))
                    session.width, session.height = img.size
                    logger.info(
                        f"Stream {stream_key} resolution: {session.width}x{session.height}"
                    )
                except Exception as e:
                    logger.warning(f"Could not extract frame dimensions: {e}")

            # Log progress periodically
            if session.frames_received % 60 == 0:  # Every 60 frames (~1 minute at 1fps)
                logger.info(
                    f"Stream {stream_key}: {session.frames_received} frames received, "
                    f"{session.frames_stored} stored"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to ingest frame for {stream_key}: {e}")
            return False

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
            # Stop processor
            if session.processor:
                try:
                    session.processor.stop_stream()
                except Exception as e:
                    logger.error(f"Error stopping processor for {stream_key}: {e}")
                session.processor = None

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

        Uses the configured host (can be overridden via RTMP_HOST env var).

        Args:
            stream_key: Stream key

        Returns:
            RTMP URL string for OBS Server field
        """
        host = config.streaming.rtmp.host
        return f"rtmp://{host}:{self.port}/live/{stream_key}"

    def get_server_url(self) -> str:
        """
        Get the base RTMP server URL (without stream key).

        Returns:
            RTMP server URL for OBS Server field
        """
        host = config.streaming.rtmp.host
        return f"rtmp://{host}:{self.port}/live"

    def get_status(self) -> dict:
        """Get server status and statistics."""
        active_streams = sum(1 for s in self.sessions.values() if s.status == "live")

        return {
            "server": {
                "active": active_streams > 0,
                "host": config.streaming.rtmp.host,
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
                        "stream_name": s.stream_name,
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
