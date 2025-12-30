"""Settings service for managing application configuration."""

import logging
from pathlib import Path

import yaml

from src.api.models import (
    CaptureAudioSettingsResponse,
    CaptureFrameSettingsResponse,
    CaptureSettingsResponse,
    CaptureSettingsUpdate,
    DefaultSettingsResponse,
    SettingsResponse,
    StreamingSettingsResponse,
    StreamingSettingsUpdate,
    STTDSettingsResponse,
    STTDSettingsUpdate,
    UpdateSettingsRequest,
    UpdateSettingsResponse,
)
from src.config import (
    CaptureAudioConfig,
    CaptureConfig,
    CaptureFrameConfig,
    Config,
    StreamingCaptureConfig,
    StreamingConfig,
    StreamingRTMPConfig,
    STTDConfig,
    config,
)

logger = logging.getLogger(__name__)

# Settings that require a restart to take effect
RESTART_REQUIRED_SETTINGS = {
    "sttd.host": "STTD server connection needs reconnect",
    "sttd.port": "STTD server connection needs reconnect",
    "streaming.max_concurrent_streams": "RTMP server configuration",
}


def _find_config_path() -> Path | None:
    """Find the config.yaml file path."""
    current = Path.cwd()
    config_paths = [
        current / "config.yaml",
        current.parent / "config.yaml",
        Path(__file__).parent.parent.parent / "config.yaml",
    ]
    for config_path in config_paths:
        if config_path.exists():
            return config_path
    return None


def _config_to_dict(cfg: Config) -> dict:
    """Convert Config object to dictionary for YAML serialization."""
    return {
        "database": {"path": cfg.database.path},
        "capture": {
            "frame": {
                "interval_seconds": cfg.capture.frame.interval_seconds,
                "jpeg_quality": cfg.capture.frame.jpeg_quality,
                "enable_deduplication": cfg.capture.frame.enable_deduplication,
                "similarity_threshold": cfg.capture.frame.similarity_threshold,
            },
            "audio": {
                "chunk_duration_seconds": cfg.capture.audio.chunk_duration_seconds,
                "sample_rate": cfg.capture.audio.sample_rate,
            },
        },
        "sttd": {
            "host": cfg.sttd.host,
            "port": cfg.sttd.port,
            "timeout": cfg.sttd.timeout,
        },
        "files": {
            "filename_format": cfg.files.filename_format,
            "filename_regex": cfg.files.filename_regex,
        },
        "api": {
            "host": cfg.api.host,
            "port": cfg.api.port,
            "max_upload_size": cfg.api.max_upload_size,
            "default_time_range_days": cfg.api.default_time_range_days,
        },
        "streaming": {
            "rtmp": {
                "enabled": cfg.streaming.rtmp.enabled,
                "port": cfg.streaming.rtmp.port,
                "max_concurrent_streams": cfg.streaming.rtmp.max_concurrent_streams,
            },
            "capture": {
                "frame_interval_seconds": cfg.streaming.capture.frame_interval_seconds,
                "buffer_size": cfg.streaming.capture.buffer_size,
                "max_frame_width": cfg.streaming.capture.max_frame_width,
                "max_frame_height": cfg.streaming.capture.max_frame_height,
            },
            "auth": {"require_stream_key": cfg.streaming.auth.require_stream_key},
        },
        "logging": {
            "level": cfg.logging.level,
            "format": cfg.logging.format,
        },
    }


def save_config(cfg: Config) -> bool:
    """
    Save configuration to YAML file.

    Args:
        cfg: Configuration object to save

    Returns:
        True if saved successfully, False otherwise
    """
    config_path = _find_config_path()
    if config_path is None:
        logger.warning("No config.yaml found, creating new one")
        config_path = Path.cwd() / "config.yaml"

    try:
        config_dict = _config_to_dict(cfg)
        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        return False


class SettingsService:
    """Service for managing application settings."""

    def get_settings(self) -> SettingsResponse:
        """Get current settings from in-memory config."""
        return SettingsResponse(
            capture=CaptureSettingsResponse(
                frame=CaptureFrameSettingsResponse(
                    interval_seconds=config.capture.frame.interval_seconds,
                    jpeg_quality=config.capture.frame.jpeg_quality,
                    enable_deduplication=config.capture.frame.enable_deduplication,
                    similarity_threshold=config.capture.frame.similarity_threshold,
                ),
                audio=CaptureAudioSettingsResponse(
                    chunk_duration_seconds=config.capture.audio.chunk_duration_seconds,
                    sample_rate=config.capture.audio.sample_rate,
                ),
            ),
            sttd=STTDSettingsResponse(
                host=config.sttd.host,
                port=config.sttd.port,
                timeout=config.sttd.timeout,
            ),
            streaming=StreamingSettingsResponse(
                frame_interval_seconds=config.streaming.capture.frame_interval_seconds,
                max_concurrent_streams=config.streaming.rtmp.max_concurrent_streams,
            ),
        )

    def get_defaults(self) -> DefaultSettingsResponse:
        """Get default settings values."""
        default_config = Config()
        return DefaultSettingsResponse(
            capture=CaptureSettingsResponse(
                frame=CaptureFrameSettingsResponse(
                    interval_seconds=default_config.capture.frame.interval_seconds,
                    jpeg_quality=default_config.capture.frame.jpeg_quality,
                    enable_deduplication=default_config.capture.frame.enable_deduplication,
                    similarity_threshold=default_config.capture.frame.similarity_threshold,
                ),
                audio=CaptureAudioSettingsResponse(
                    chunk_duration_seconds=default_config.capture.audio.chunk_duration_seconds,
                    sample_rate=default_config.capture.audio.sample_rate,
                ),
            ),
            sttd=STTDSettingsResponse(
                host=default_config.sttd.host,
                port=default_config.sttd.port,
                timeout=default_config.sttd.timeout,
            ),
            streaming=StreamingSettingsResponse(
                frame_interval_seconds=default_config.streaming.capture.frame_interval_seconds,
                max_concurrent_streams=default_config.streaming.rtmp.max_concurrent_streams,
            ),
        )

    def update_settings(self, request: UpdateSettingsRequest) -> UpdateSettingsResponse:
        """
        Update settings.

        Updates both in-memory config and persists to config.yaml.
        Returns which settings require restart to take effect.
        """
        global config
        restart_required = False
        restart_reasons = []

        # Track changes that require restart (STTD client reconnect)
        if request.sttd:
            if request.sttd.host is not None and request.sttd.host != config.sttd.host:
                restart_required = True
                restart_reasons.append(RESTART_REQUIRED_SETTINGS["sttd.host"])
            if request.sttd.port is not None and request.sttd.port != config.sttd.port:
                restart_required = True
                restart_reasons.append(RESTART_REQUIRED_SETTINGS["sttd.port"])

        if request.streaming:
            if (
                request.streaming.max_concurrent_streams is not None
                and request.streaming.max_concurrent_streams
                != config.streaming.rtmp.max_concurrent_streams
            ):
                restart_required = True
                restart_reasons.append(
                    RESTART_REQUIRED_SETTINGS["streaming.max_concurrent_streams"]
                )

        # Apply updates to in-memory config
        if request.capture:
            self._update_capture_settings(request.capture)
        if request.sttd:
            self._update_sttd_settings(request.sttd)
        if request.streaming:
            self._update_streaming_settings(request.streaming)

        # Persist to config.yaml
        save_config(config)

        return UpdateSettingsResponse(
            settings=self.get_settings(),
            restart_required=restart_required,
            restart_reason="; ".join(restart_reasons) if restart_reasons else None,
        )

    def _update_capture_settings(self, update: CaptureSettingsUpdate) -> None:
        """Update capture settings in-memory."""
        if update.frame:
            frame = config.capture.frame
            new_frame = CaptureFrameConfig(
                interval_seconds=(
                    update.frame.interval_seconds
                    if update.frame.interval_seconds is not None
                    else frame.interval_seconds
                ),
                jpeg_quality=(
                    update.frame.jpeg_quality
                    if update.frame.jpeg_quality is not None
                    else frame.jpeg_quality
                ),
                enable_deduplication=(
                    update.frame.enable_deduplication
                    if update.frame.enable_deduplication is not None
                    else frame.enable_deduplication
                ),
                similarity_threshold=(
                    update.frame.similarity_threshold
                    if update.frame.similarity_threshold is not None
                    else frame.similarity_threshold
                ),
            )
            config.capture = CaptureConfig(frame=new_frame, audio=config.capture.audio)

        if update.audio:
            audio = config.capture.audio
            new_audio = CaptureAudioConfig(
                chunk_duration_seconds=(
                    update.audio.chunk_duration_seconds
                    if update.audio.chunk_duration_seconds is not None
                    else audio.chunk_duration_seconds
                ),
                sample_rate=(
                    update.audio.sample_rate
                    if update.audio.sample_rate is not None
                    else audio.sample_rate
                ),
            )
            config.capture = CaptureConfig(frame=config.capture.frame, audio=new_audio)

    def _update_sttd_settings(self, update: STTDSettingsUpdate) -> None:
        """Update STTD settings in-memory."""
        sttd = config.sttd
        new_sttd = STTDConfig(
            host=update.host if update.host is not None else sttd.host,
            port=update.port if update.port is not None else sttd.port,
            timeout=update.timeout if update.timeout is not None else sttd.timeout,
        )
        # Update the global config
        import src.config

        src.config.config = Config(
            database=config.database,
            capture=config.capture,
            sttd=new_sttd,
            files=config.files,
            api=config.api,
            streaming=config.streaming,
            logging=config.logging,
        )

        # Reset the STTD client to use new connection settings
        from src.capture.sttd_client import reset_sttd_client

        reset_sttd_client()

    def _update_streaming_settings(self, update: StreamingSettingsUpdate) -> None:
        """Update streaming settings in-memory."""
        streaming = config.streaming
        new_rtmp = StreamingRTMPConfig(
            enabled=streaming.rtmp.enabled,
            port=streaming.rtmp.port,
            max_concurrent_streams=(
                update.max_concurrent_streams
                if update.max_concurrent_streams is not None
                else streaming.rtmp.max_concurrent_streams
            ),
        )
        new_capture = StreamingCaptureConfig(
            frame_interval_seconds=(
                update.frame_interval_seconds
                if update.frame_interval_seconds is not None
                else streaming.capture.frame_interval_seconds
            ),
            buffer_size=streaming.capture.buffer_size,
            max_frame_width=streaming.capture.max_frame_width,
            max_frame_height=streaming.capture.max_frame_height,
        )
        new_streaming = StreamingConfig(
            rtmp=new_rtmp,
            capture=new_capture,
            auth=streaming.auth,
        )
        # Update the global config
        import src.config

        src.config.config = Config(
            database=config.database,
            capture=config.capture,
            sttd=config.sttd,
            files=config.files,
            api=config.api,
            streaming=new_streaming,
            logging=config.logging,
        )
