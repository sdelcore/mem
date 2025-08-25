"""Main capture pipeline for video processing."""

import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from src.capture.extractor import (
    parse_video_timestamp,
    get_video_duration,
    get_video_info,
    extract_frames,
    extract_audio,
    get_audio_chunks,
)
from src.capture.transcriber import Transcriber
from src.storage.db import Database
from src.storage.models import Source, Frame, Transcription
from src.config import config as app_config

logger = logging.getLogger(__name__)


class CaptureConfig:
    """Configuration for capture pipeline."""

    def __init__(
        self,
        frame_interval: int = None,
        chunk_duration: int = None,
        image_quality: int = None,
        whisper_model: str = None,
        whisper_language: str = None,
    ):
        """
        Initialize capture configuration.

        Args:
            frame_interval: Seconds between frame extraction (uses config default if None)
            chunk_duration: Audio chunk duration in seconds (uses config default if None)
            image_quality: JPEG quality (1-100) (uses config default if None)
            whisper_model: Whisper model size (uses config default if None)
            whisper_language: Language for transcription or "auto" (uses config default if None)
        """
        self.frame_interval = frame_interval or app_config.capture.frame.interval_seconds
        self.chunk_duration = chunk_duration or app_config.capture.audio.chunk_duration_seconds
        self.image_quality = image_quality or app_config.capture.frame.jpeg_quality
        self.whisper_model = whisper_model or app_config.whisper.model
        self.whisper_language = whisper_language or app_config.whisper.language
        if self.whisper_language == "auto":
            self.whisper_language = None


class VideoCaptureProcessor:
    """Processes videos to extract frames and transcriptions."""

    def __init__(self, db_path: str = None, config: Optional[CaptureConfig] = None):
        """
        Initialize processor.

        Args:
            db_path: Path to database
            config: Capture configuration
        """
        self.db = Database(db_path or app_config.database.path)
        self.config = config or CaptureConfig()
        self.transcriber = Transcriber(model_name=self.config.whisper_model)
        # Pre-load the Whisper model to avoid delays during processing
        logger.info("Pre-loading Whisper model...")
        self.transcriber.load_model()
        logger.info("Whisper model ready")

    def process_video(self, video_path: Path) -> Dict[str, Any]:
        """
        Process a video file to extract frames and transcriptions.

        Args:
            video_path: Path to video file (must be YYYY-MM-DD_HH-MM-SS format)

        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing video: {video_path}")

        # Validate filename and parse timestamp
        try:
            start_timestamp = parse_video_timestamp(video_path.name)
        except ValueError as e:
            logger.error(f"Invalid filename: {e}")
            return {"status": "error", "error": str(e)}

        # Get video info
        video_info = get_video_info(video_path)
        duration = video_info["duration"]
        end_timestamp = start_timestamp + timedelta(seconds=duration)

        # Connect to database
        self.db.connect()
        self.db.initialize()

        try:
            # Create source record
            source = Source(
                type="video",
                filename=video_path.name,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                duration_seconds=duration,
                metadata=video_info,
            )
            source_id = self.db.create_source(source)
            logger.info(f"Created source {source_id} for {video_path.name}")

            # Extract and store frames
            logger.info("About to extract frames...")
            frame_count = self._process_frames(video_path, source_id, start_timestamp)
            logger.info(f"Frame extraction complete: {frame_count} frames")

            # Extract and transcribe audio
            logger.info("Starting audio processing...")
            try:
                transcript_count = self._process_audio(video_path, source_id, start_timestamp)
            except Exception as e:
                logger.error(f"Audio processing failed: {e}", exc_info=True)
                transcript_count = 0

            # Update source with counts
            self.db.update_source_end(source_id, end_timestamp, duration, frame_count)

            return {
                "status": "success",
                "source_id": source_id,
                "frames_extracted": frame_count,
                "transcriptions_created": transcript_count,
                "duration_seconds": duration,
                "start_time": start_timestamp.isoformat(),
                "end_time": end_timestamp.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            self.db.disconnect()

    def _process_frames(self, video_path: Path, source_id: int, start_timestamp: datetime) -> int:
        """
        Extract and store frames from video.

        Returns:
            Number of frames extracted
        """
        logger.info(f"Extracting frames every {self.config.frame_interval} seconds")

        frame_count = 0
        for relative_seconds, jpeg_bytes in extract_frames(
            video_path, interval=self.config.frame_interval, quality=self.config.image_quality
        ):
            # Calculate absolute timestamp
            absolute_timestamp = start_timestamp + timedelta(seconds=relative_seconds)

            # Create frame record
            frame = Frame(
                source_id=source_id,
                timestamp=absolute_timestamp,
                image_data=jpeg_bytes,
                width=0,  # Will be updated from actual image
                height=0,  # Will be updated from actual image
                format="jpeg",
            )

            # Get dimensions from image
            from PIL import Image
            from io import BytesIO

            img = Image.open(BytesIO(jpeg_bytes))
            frame.width = img.width
            frame.height = img.height

            # Store frame
            frame_id = self.db.store_frame(frame)
            frame_count += 1

            if frame_count % 10 == 0:
                logger.info(f"Extracted {frame_count} frames")

        logger.info(f"Total frames extracted: {frame_count}")
        return frame_count

    def _process_audio(self, video_path: Path, source_id: int, start_timestamp: datetime) -> int:
        """
        Extract and transcribe audio from video.

        Returns:
            Number of transcriptions created
        """
        logger.info(f"Extracting audio for transcription")

        # Extract audio to temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "audio.wav"

            try:
                audio_path = extract_audio(video_path, audio_path)
                logger.info(f"Audio extracted successfully: {audio_path.stat().st_size} bytes")
            except RuntimeError as e:
                logger.warning(f"Could not extract audio: {e}")
                return 0

            # Detect language if auto
            if self.config.whisper_language is None:
                try:
                    language = self.transcriber.detect_language(audio_path)
                    logger.info(f"Detected language: {language}")
                except Exception as e:
                    logger.warning(f"Language detection failed: {e}")
                    language = app_config.whisper.fallback_language  # Default to fallback language
            else:
                language = self.config.whisper_language
                logger.info(f"Using configured language: {language}")

            # Process audio in chunks
            transcript_count = 0
            chunk_count = 0
            for chunk in get_audio_chunks(audio_path, self.config.chunk_duration):
                chunk_count += 1
                logger.info(
                    f"Processing chunk {chunk['index']}: {chunk['start_seconds']:.1f}s - {chunk['end_seconds']:.1f}s"
                )

                chunk_start = start_timestamp + timedelta(seconds=chunk["start_seconds"])
                chunk_end = start_timestamp + timedelta(seconds=chunk["end_seconds"])

                # Transcribe chunk
                try:
                    result = self.transcriber.transcribe_chunk(
                        chunk["audio_data"], chunk["sample_rate"], language
                    )
                    logger.info(f"Transcription result: {len(result.get('text', ''))} chars")
                except Exception as e:
                    logger.error(f"Transcription failed for chunk {chunk['index']}: {e}")
                    continue

                if result["text"].strip():  # Only store non-empty transcriptions
                    # Calculate confidence
                    confidence = self.transcriber.calculate_confidence(result.get("segments", []))

                    # Create transcription record
                    transcription = Transcription(
                        source_id=source_id,
                        start_timestamp=chunk_start,
                        end_timestamp=chunk_end,
                        text=result["text"],
                        confidence=confidence,
                        language=result.get("language", language),
                    )

                    # Store transcription
                    self.db.store_transcription(transcription)
                    transcript_count += 1

                    logger.info(
                        f"Transcribed chunk {chunk['index']}: {len(result['text'])} chars, confidence: {confidence:.2f}"
                    )
                else:
                    logger.info(f"Chunk {chunk['index']} had no text content")

            logger.info(f"Processed {chunk_count} chunks")
        logger.info(f"Total transcriptions created: {transcript_count}")
        return transcript_count


class StreamCaptureProcessor:
    """Processes live streams to extract frames and transcriptions."""

    def __init__(self, db_path: str = None, config: Optional[CaptureConfig] = None):
        """
        Initialize stream processor.

        Args:
            db_path: Path to database
            config: Capture configuration
        """
        self.db = Database(db_path or app_config.database.path)
        self.config = config or CaptureConfig()
        self.transcriber = Transcriber(model_name=self.config.whisper_model)
        self.active = False
        self.source_id = None

    def start_stream(self, stream_type: str = "webcam") -> int:
        """
        Start capturing from stream.

        Args:
            stream_type: Type of stream (webcam, screen, etc.)

        Returns:
            Source ID for the stream
        """
        self.db.connect()
        self.db.initialize()

        # Create source record
        start_timestamp = datetime.utcnow()
        source = Source(
            type="stream",
            filename=f"stream_{start_timestamp.strftime('%Y%m%d_%H%M%S')}",
            start_timestamp=start_timestamp,
            metadata={"stream_type": stream_type},
        )
        self.source_id = self.db.create_source(source)
        self.active = True

        logger.info(f"Started stream capture with source ID {self.source_id}")
        return self.source_id

    def capture_frame(self, frame_data: bytes, width: int, height: int):
        """
        Capture a single frame from stream.

        Args:
            frame_data: JPEG frame data
            width: Frame width
            height: Frame height
        """
        if not self.active or not self.source_id:
            raise RuntimeError("Stream not active")

        timestamp = datetime.utcnow()

        frame = Frame(
            source_id=self.source_id,
            timestamp=timestamp,
            image_data=frame_data,
            width=width,
            height=height,
            format="jpeg",
        )

        self.db.store_frame(frame)

    def stop_stream(self):
        """Stop stream capture."""
        if self.active and self.source_id:
            end_timestamp = datetime.utcnow()
            source = self.db.get_source(self.source_id)

            if source:
                duration = (end_timestamp - source.start_timestamp).total_seconds()

                # Count frames
                frames = self.db.get_frames_by_time_range(
                    source.start_timestamp, end_timestamp, self.source_id
                )

                self.db.update_source_end(self.source_id, end_timestamp, duration, len(frames))

            self.active = False
            self.source_id = None
            self.db.disconnect()

            logger.info("Stream capture stopped")
