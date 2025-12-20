"""Configuration management for Mem."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class CaptureFrameConfig(BaseModel):
    """Frame capture configuration."""

    interval_seconds: int = 5
    jpeg_quality: int = 85
    enable_deduplication: bool = True  # Enable perceptual hash deduplication
    similarity_threshold: float = (
        95.0  # Threshold for considering frames similar (0-100)
    )


class CaptureAudioConfig(BaseModel):
    """Audio capture configuration."""

    chunk_duration_seconds: int = 300
    sample_rate: int = 16000


class CaptureConfig(BaseModel):
    """Capture configuration."""

    frame: CaptureFrameConfig = CaptureFrameConfig()
    audio: CaptureAudioConfig = CaptureAudioConfig()


class WhisperConfig(BaseModel):
    """Whisper transcription configuration (legacy, use STTDConfig instead)."""

    model: str = "base"
    language: str = "auto"
    fallback_language: str = "en"
    device: str = "cpu"
    detect_non_speech: bool = True
    no_speech_threshold: float = 0.6
    logprob_threshold: float = -1.0


class STTDConfig(BaseModel):
    """STTD (speech-to-text with diarization) configuration."""

    model: str = "large-v3"  # Whisper model size
    device: str = "cuda"  # cuda or cpu
    compute_type: str = "float16"  # float16 for GPU, int8 for CPU
    profiles_path: str = "data/voice_profiles"  # Storage for voice profiles
    enable_diarization: bool = True  # Enable speaker identification
    speaker_identification: bool = True  # Identify registered speakers
    min_speaker_confidence: float = 0.7  # Threshold for speaker ID


class DatabaseConfig(BaseModel):
    """Database configuration."""

    path: str = "mem.db"


class FilesConfig(BaseModel):
    """File handling configuration."""

    filename_format: str = "YYYY-MM-DD_HH-MM-SS"
    filename_regex: str = r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})$"


class APIConfig(BaseModel):
    """API server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    max_upload_size: int = 5368709120  # 5GB
    default_time_range_days: int = 1


class StreamingRTMPConfig(BaseModel):
    """RTMP streaming configuration."""

    enabled: bool = True
    port: int = 1935
    max_concurrent_streams: int = 10


class StreamingCaptureConfig(BaseModel):
    """Streaming capture configuration."""

    frame_interval_seconds: int = 1
    buffer_size: int = 30
    max_frame_width: int = 7680
    max_frame_height: int = 4320


class StreamingAuthConfig(BaseModel):
    """Streaming authentication configuration."""

    require_stream_key: bool = True


class StreamingConfig(BaseModel):
    """Streaming configuration."""

    rtmp: StreamingRTMPConfig = StreamingRTMPConfig()
    capture: StreamingCaptureConfig = StreamingCaptureConfig()
    auth: StreamingAuthConfig = StreamingAuthConfig()


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    debug_level: str = "DEBUG"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class Config(BaseModel):
    """Main configuration class."""

    database: DatabaseConfig = DatabaseConfig()
    capture: CaptureConfig = CaptureConfig()
    whisper: WhisperConfig = WhisperConfig()  # Legacy, use sttd
    sttd: STTDConfig = STTDConfig()
    files: FilesConfig = FilesConfig()
    api: APIConfig = APIConfig()
    streaming: StreamingConfig = StreamingConfig()
    logging: LoggingConfig = LoggingConfig()


def load_config(path: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file or use defaults.

    Args:
        path: Optional path to config file. Defaults to config.yaml in project root.

    Returns:
        Config object with loaded or default settings.
    """
    if path is None:
        # Look for config.yaml in current directory or parent directories
        current = Path.cwd()
        config_paths = [
            current / "config.yaml",
            current.parent / "config.yaml",
            Path(__file__).parent.parent / "config.yaml",
        ]

        for config_path in config_paths:
            if config_path.exists():
                path = config_path
                break
        else:
            # No config file found, use defaults
            return Config()

    if path and path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # Parse nested config structure
        streaming_data = data.get("streaming", {})
        return Config(
            database=DatabaseConfig(**data.get("database", {})),
            capture=CaptureConfig(
                frame=CaptureFrameConfig(**data.get("capture", {}).get("frame", {})),
                audio=CaptureAudioConfig(**data.get("capture", {}).get("audio", {})),
            ),
            whisper=WhisperConfig(**data.get("whisper", {})),
            sttd=STTDConfig(**data.get("sttd", {})),
            files=FilesConfig(**data.get("files", {})),
            api=APIConfig(**data.get("api", {})),
            streaming=StreamingConfig(
                rtmp=StreamingRTMPConfig(**streaming_data.get("rtmp", {})),
                capture=StreamingCaptureConfig(**streaming_data.get("capture", {})),
                auth=StreamingAuthConfig(**streaming_data.get("auth", {})),
            ),
            logging=LoggingConfig(**data.get("logging", {})),
        )
    else:
        # Return default config if file doesn't exist
        return Config()


# Global config instance - loaded once when module is imported
config = load_config()
