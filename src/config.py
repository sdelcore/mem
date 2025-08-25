"""Configuration management for Mem."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel


class CaptureFrameConfig(BaseModel):
    """Frame capture configuration."""

    interval_seconds: int = 5
    jpeg_quality: int = 85


class CaptureAudioConfig(BaseModel):
    """Audio capture configuration."""

    chunk_duration_seconds: int = 300
    sample_rate: int = 16000


class CaptureConfig(BaseModel):
    """Capture configuration."""

    frame: CaptureFrameConfig = CaptureFrameConfig()
    audio: CaptureAudioConfig = CaptureAudioConfig()


class WhisperConfig(BaseModel):
    """Whisper transcription configuration."""

    model: str = "base"
    language: str = "auto"
    fallback_language: str = "en"
    device: str = "cpu"


class DatabaseConfig(BaseModel):
    """Database configuration."""

    path: str = "mem.db"


class FilesConfig(BaseModel):
    """File handling configuration."""

    video_pattern: str = "*.mp4"
    filename_format: str = "YYYY-MM-DD_HH-MM-SS"
    filename_regex: str = r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})$"


class DisplayConfig(BaseModel):
    """CLI display configuration."""

    frames_limit: int = 100
    default_time_range_days: int = 1


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    debug_level: str = "DEBUG"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class Config(BaseModel):
    """Main configuration class."""

    database: DatabaseConfig = DatabaseConfig()
    capture: CaptureConfig = CaptureConfig()
    whisper: WhisperConfig = WhisperConfig()
    files: FilesConfig = FilesConfig()
    display: DisplayConfig = DisplayConfig()
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
        return Config(
            database=DatabaseConfig(**data.get("database", {})),
            capture=CaptureConfig(
                frame=CaptureFrameConfig(**data.get("capture", {}).get("frame", {})),
                audio=CaptureAudioConfig(**data.get("capture", {}).get("audio", {})),
            ),
            whisper=WhisperConfig(**data.get("whisper", {})),
            files=FilesConfig(**data.get("files", {})),
            display=DisplayConfig(**data.get("display", {})),
            logging=LoggingConfig(**data.get("logging", {})),
        )
    else:
        # Return default config if file doesn't exist
        return Config()


# Global config instance - loaded once when module is imported
config = load_config()
