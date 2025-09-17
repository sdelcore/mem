"""Main capture pipeline for video processing."""

import logging
import tempfile
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from src.capture.extractor import (
    extract_audio,
    extract_frames,
    get_audio_chunks,
    get_video_info,
    parse_video_timestamp,
)
from src.capture.frame import FrameProcessor
from src.capture.transcriber import Transcriber
from src.config import config as app_config
from src.storage.db import Database
from src.storage.models import Frame, Source, Timeline, Transcription

logger = logging.getLogger(__name__)


class CaptureConfig:
    """Configuration for capture pipeline."""

    def __init__(
        self,
        frame_interval: int = None,
        chunk_duration: int = None,
        overlap_seconds: int = None,
        image_quality: int = None,
        whisper_model: str = None,
        whisper_language: str = None,
    ):
        """
        Initialize capture configuration.

        Args:
            frame_interval: Seconds between frame extraction (uses config default if None)
            chunk_duration: Audio chunk duration in seconds (uses config default if None)
            overlap_seconds: Overlap between audio chunks in seconds (uses config default if None)
            image_quality: JPEG quality (1-100) (uses config default if None)
            whisper_model: Whisper model size (uses config default if None)
            whisper_language: Language for transcription or "auto" (uses config default if None)
        """
        self.frame_interval = (
            frame_interval or app_config.capture.frame.interval_seconds
        )
        self.chunk_duration = (
            chunk_duration or app_config.capture.audio.chunk_duration_seconds
        )
        self.overlap_seconds = overlap_seconds or getattr(
            app_config.capture.audio, "overlap_seconds", 0
        )
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
        # Initialize frame processor with config settings
        self.enable_deduplication = app_config.capture.frame.enable_deduplication
        self.frame_processor = FrameProcessor(
            similarity_threshold=app_config.capture.frame.similarity_threshold
        )
        # Pre-load the Whisper model to avoid delays during processing
        logger.info("Pre-loading Whisper model...")
        self.transcriber.load_model()
        logger.info("Whisper model ready")

    def process_video(self, video_path: Path) -> dict[str, Any]:
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
            # Create source record with video info in metadata
            source = Source(
                type="video",
                filename=video_path.name,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                metadata=video_info,  # Contains fps, width, height, duration, etc.
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
                transcript_count = self._process_audio(
                    video_path, source_id, start_timestamp
                )
            except Exception as e:
                logger.error(f"Audio processing failed: {e}", exc_info=True)
                transcript_count = 0

            # Update source with end timestamp
            self.db.update_source_end(source_id, end_timestamp, duration)

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

    def _process_frames(
        self, video_path: Path, source_id: int, start_timestamp: datetime
    ) -> int:
        """
        Extract and store frames from video with deduplication.

        Returns:
            Number of unique frames stored
        """
        logger.info(
            f"Extracting frames every {self.config.frame_interval} seconds with deduplication"
        )

        frame_count = 0
        timeline_count = 0
        skipped_count = 0

        for relative_seconds, jpeg_bytes in extract_frames(
            video_path,
            interval=self.config.frame_interval,
            quality=self.config.image_quality,
        ):
            # Calculate absolute timestamp
            absolute_timestamp = start_timestamp + timedelta(seconds=relative_seconds)
            timeline_count += 1

            frame_id = None
            similarity = 0.0

            if self.enable_deduplication:
                # Check if frame should be stored (deduplication enabled)
                should_store, perceptual_hash, similarity = (
                    self.frame_processor.should_store_frame(source_id, jpeg_bytes)
                )
            else:
                # No deduplication - always store frame
                should_store = True
                perceptual_hash = self.frame_processor.calculate_hash(jpeg_bytes)

            if should_store:
                # Create frame record with metadata
                frame = Frame(
                    source_id=source_id,
                    first_seen_timestamp=absolute_timestamp,
                    last_seen_timestamp=absolute_timestamp,
                    perceptual_hash=perceptual_hash,
                    image_data=jpeg_bytes,
                    metadata={
                        "jpeg_quality": self.config.image_quality,
                        "processing_params": {
                            "similarity_threshold": self.frame_processor.similarity_threshold
                        },
                    },
                )

                # Store frame
                frame_id = self.db.store_frame(frame)
                frame_count += 1
                logger.debug(f"Stored new frame {frame_id} at {absolute_timestamp}")
            elif self.enable_deduplication:
                # Find existing frame with this hash (only if deduplication is enabled)
                frame_id = self.db.find_similar_frame(source_id, perceptual_hash)
                if frame_id:
                    # Update last seen timestamp for existing frame
                    self.db.update_frame_last_seen(frame_id, absolute_timestamp)
                    skipped_count += 1
                    logger.debug(
                        f"Skipped duplicate frame at {absolute_timestamp} (similarity: {similarity:.1f}%)"
                    )

            # Create timeline entry
            timeline = Timeline(
                source_id=source_id,
                timestamp=absolute_timestamp,
                frame_id=frame_id,
                similarity_score=similarity,
            )
            self.db.create_timeline_entry(timeline)

            if timeline_count % 10 == 0:
                logger.info(
                    f"Processed {timeline_count} frames: {frame_count} unique, {skipped_count} duplicates"
                )

        # Log deduplication stats
        dedup_percentage = (
            (skipped_count / timeline_count * 100) if timeline_count > 0 else 0
        )
        logger.info(
            f"Frame extraction complete: {timeline_count} total, {frame_count} unique, {skipped_count} duplicates ({dedup_percentage:.1f}% deduplication)"
        )

        return frame_count

    def _process_audio(
        self, video_path: Path, source_id: int, start_timestamp: datetime
    ) -> int:
        """
        Extract and transcribe audio from video.

        Returns:
            Number of transcriptions created
        """
        logger.info("Extracting audio for transcription")

        # Extract audio to temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "audio.wav"

            try:
                audio_path = extract_audio(video_path, audio_path)
                logger.info(
                    f"Audio extracted successfully: {audio_path.stat().st_size} bytes"
                )
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
                    language = (
                        app_config.whisper.fallback_language
                    )  # Default to fallback language
            else:
                language = self.config.whisper_language
                logger.info(f"Using configured language: {language}")

            # Process audio in chunks with overlap
            transcript_count = 0
            chunk_count = 0
            for chunk in get_audio_chunks(
                audio_path, self.config.chunk_duration, self.config.overlap_seconds
            ):
                chunk_count += 1
                logger.info(
                    f"Processing chunk {chunk['index']}: {chunk['start_seconds']:.1f}s - {chunk['end_seconds']:.1f}s"
                )

                chunk_start = start_timestamp + timedelta(
                    seconds=chunk["start_seconds"]
                )
                chunk_end = start_timestamp + timedelta(seconds=chunk["end_seconds"])

                # Transcribe chunk
                try:
                    result = self.transcriber.transcribe_chunk(
                        chunk["audio_data"], chunk["sample_rate"], language
                    )

                    # Check if non-speech was detected
                    if result.get("is_non_speech", False):
                        audio_type = result.get("audio_type", "[Non-Speech Audio]")
                        logger.info(
                            f"Non-speech audio detected in chunk {chunk['index']}: {audio_type}"
                        )
                    else:
                        logger.info(
                            f"Transcription result: {len(result.get('text', ''))} chars"
                        )
                except Exception as e:
                    logger.error(
                        f"Transcription failed for chunk {chunk['index']}: {e}"
                    )
                    continue

                # Store transcriptions including non-speech markers
                text = result.get("text", "").strip()
                if text or result.get(
                    "is_non_speech", False
                ):  # Store non-empty or non-speech
                    # Calculate confidence
                    confidence = self.transcriber.calculate_confidence(
                        result.get("segments", [])
                    )

                    # Determine overlap timestamps if any
                    overlap_start_ts = None
                    overlap_end_ts = None
                    if chunk.get("overlap_start_seconds") is not None:
                        overlap_start_ts = start_timestamp + timedelta(
                            seconds=chunk["overlap_start_seconds"]
                        )
                    if chunk.get("overlap_end_seconds") is not None:
                        overlap_end_ts = start_timestamp + timedelta(
                            seconds=chunk["overlap_end_seconds"]
                        )

                    # Create transcription record with overlap and non-speech metadata
                    transcription = Transcription(
                        source_id=source_id,
                        start_timestamp=chunk_start,
                        end_timestamp=chunk_end,
                        text=result.get("text", ""),
                        confidence=confidence,
                        language=result.get("language", language),
                        whisper_model=self.config.whisper_model,
                        has_overlap=chunk.get("has_overlap", False),
                        overlap_start=overlap_start_ts,
                        overlap_end=overlap_end_ts,
                        metadata=(
                            {
                                "is_non_speech": result.get("is_non_speech", False),
                                "audio_type": result.get("audio_type", None),
                            }
                            if result.get("is_non_speech", False)
                            else None
                        ),
                    )

                    # Store transcription
                    trans_id = self.db.store_transcription(transcription)
                    transcript_count += 1

                    # Update timeline entries in this time range to reference this transcription
                    self.db.update_timeline_transcriptions(
                        source_id, chunk_start, chunk_end, trans_id
                    )

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
        # Initialize frame processor with config settings
        self.enable_deduplication = app_config.capture.frame.enable_deduplication
        self.frame_processor = FrameProcessor(
            similarity_threshold=app_config.capture.frame.similarity_threshold
        )
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
        start_timestamp = datetime.now()
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

    def capture_frame(self, frame_data: bytes):
        """
        Capture a single frame from stream with deduplication.
        Automatically detects frame dimensions from JPEG data.

        Args:
            frame_data: JPEG frame data (any resolution)
        """
        if not self.active or not self.source_id:
            raise RuntimeError("Stream not active")

        timestamp = datetime.now()

        # Auto-detect dimensions from JPEG header
        try:
            img = Image.open(BytesIO(frame_data))
            width, height = img.size
        except Exception as e:
            logger.error(f"Failed to parse frame dimensions: {e}")
            return

        # Check if frame should be stored (deduplication)
        should_store, perceptual_hash, similarity = (
            self.frame_processor.should_store_frame(self.source_id, frame_data)
        )

        frame_id = None

        if should_store:
            # Create frame record
            frame = Frame(
                source_id=self.source_id,
                timestamp=timestamp,
                first_seen_timestamp=timestamp,
                last_seen_timestamp=timestamp,
                perceptual_hash=perceptual_hash,
                image_data=frame_data,
                metadata={
                    "width": width,
                    "height": height,
                    "aspect_ratio": f"{width}:{height}",
                    "jpeg_quality": self.config.image_quality,
                },
            )

            # Store frame
            frame_id = self.db.store_frame(frame)
            logger.debug(
                f"Stored new frame {frame_id} at {timestamp} ({width}x{height})"
            )
        else:
            # Find existing frame with this hash
            frame_id = self.db.find_similar_frame(self.source_id, perceptual_hash)
            if frame_id:
                # Update last seen timestamp for existing frame
                self.db.update_frame_last_seen(frame_id, timestamp)
                logger.debug(
                    f"Skipped duplicate frame at {timestamp} (similarity: {similarity:.1f}%)"
                )

        # Create timeline entry
        timeline = Timeline(
            source_id=self.source_id,
            timestamp=timestamp,
            frame_id=frame_id,
            similarity_score=similarity,
        )
        self.db.create_timeline_entry(timeline)

    def stop_stream(self):
        """Stop stream capture."""
        if self.active and self.source_id:
            end_timestamp = datetime.now()
            source = self.db.get_source(self.source_id)

            if source and source.start_timestamp:
                # Handle both naive and aware datetimes
                start_ts = source.start_timestamp
                if hasattr(start_ts, "tzinfo") and start_ts.tzinfo is not None:
                    # start_timestamp is timezone-aware, make end_timestamp aware too
                    import pytz

                    end_timestamp = datetime.now(pytz.UTC)
                elif (
                    hasattr(end_timestamp, "tzinfo")
                    and end_timestamp.tzinfo is not None
                ):
                    # end_timestamp is timezone-aware, make it naive
                    end_timestamp = end_timestamp.replace(tzinfo=None)

                try:
                    duration = (end_timestamp - start_ts).total_seconds()
                    # Update source end timestamp
                    self.db.update_source_end(self.source_id, end_timestamp, duration)
                except Exception as e:
                    logger.error(f"Error calculating duration: {e}")
                    # Just update the end timestamp without duration
                    self.db.update_source_end(self.source_id, end_timestamp, 0)

                # Reset frame processor for this source
                self.frame_processor.reset_source(self.source_id)

            self.active = False
            self.source_id = None
            self.db.disconnect()

            logger.info("Stream capture stopped")
