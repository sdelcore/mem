"""HTTP client for communicating with STTD server."""

import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class STTDError(Exception):
    """Base exception for STTD client errors."""

    pass


class STTDConnectionError(STTDError):
    """Raised when unable to connect to STTD server."""

    pass


class STTDTranscriptionError(STTDError):
    """Raised when transcription fails."""

    pass


class STTDClient:
    """HTTP client for STTD transcription server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, timeout: float = 300.0):
        """Initialize STTD client.

        Args:
            host: STTD server host (default: 127.0.0.1)
            port: STTD server port (default: 8765)
            timeout: Request timeout in seconds (default: 300s for long transcriptions)
        """
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "STTDClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def health_check(self) -> bool:
        """Check if STTD server is available.

        Returns:
            True if server is healthy, False otherwise.
        """
        try:
            response = self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def get_status(self) -> dict[str, Any]:
        """Get STTD server status.

        Returns:
            Server status dictionary.

        Raises:
            STTDConnectionError: If unable to connect to server.
        """
        try:
            response = self._client.get(f"{self.base_url}/status")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise STTDConnectionError(f"Cannot connect to STTD server at {self.base_url}: {e}")
        except httpx.RequestError as e:
            raise STTDError(f"Request error: {e}")

    def transcribe_file(
        self, audio_path: Path, identify_speakers: bool = True
    ) -> dict[str, Any]:
        """Transcribe an audio file with optional speaker identification.

        Args:
            audio_path: Path to the audio file.
            identify_speakers: Whether to identify speakers in the transcription (default: True).

        Returns:
            Transcription result with segments and speaker info.

        Raises:
            STTDConnectionError: If unable to connect to server.
            STTDTranscriptionError: If transcription fails.
            FileNotFoundError: If audio file doesn't exist.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Determine content type based on extension
        content_type = self._get_content_type(audio_path)

        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            return self.transcribe_bytes(audio_data, content_type, identify_speakers)

        except httpx.ConnectError as e:
            raise STTDConnectionError(f"Cannot connect to STTD server at {self.base_url}: {e}")
        except httpx.RequestError as e:
            raise STTDError(f"Request error: {e}")

    def transcribe_bytes(
        self,
        audio_data: bytes,
        content_type: str = "audio/wav",
        identify_speakers: bool = True,
    ) -> dict[str, Any]:
        """Transcribe raw audio bytes.

        Args:
            audio_data: Raw audio bytes.
            content_type: MIME type of audio data (default: audio/wav).
            identify_speakers: Whether to identify speakers in the transcription (default: True).

        Returns:
            Transcription result with text, segments, and speaker info.

        Raises:
            STTDConnectionError: If unable to connect to server.
            STTDTranscriptionError: If transcription fails.
        """
        try:
            params = []
            if not identify_speakers:
                params.append("identify_speakers=false")

            url = f"{self.base_url}/transcribe"
            if params:
                url += "?" + "&".join(params)

            response = self._client.post(
                url,
                content=audio_data,
                headers={"Content-Type": content_type},
            )

            if response.status_code != 200:
                error_msg = response.text
                raise STTDTranscriptionError(f"Transcription failed: {error_msg}")

            return response.json()

        except httpx.ConnectError as e:
            raise STTDConnectionError(f"Cannot connect to STTD server at {self.base_url}: {e}")
        except httpx.TimeoutException as e:
            raise STTDError(f"Request timed out after {self.timeout}s: {e}")
        except httpx.RequestError as e:
            raise STTDError(f"Request error: {e}")

    def list_profiles(self) -> list[dict]:
        """List all voice profiles from STTD server.

        Returns:
            List of profile dicts with name, created_at, audio_duration.

        Raises:
            STTDConnectionError: If unable to connect to server.
            STTDError: If request fails.
        """
        try:
            response = self._client.get(f"{self.base_url}/profiles")
            response.raise_for_status()
            return response.json().get("profiles", [])
        except httpx.ConnectError as e:
            raise STTDConnectionError(f"Cannot connect to STTD server at {self.base_url}: {e}")
        except httpx.RequestError as e:
            raise STTDError(f"Request error: {e}")

    def get_profile(self, name: str) -> dict | None:
        """Get a specific voice profile.

        Args:
            name: Name of the voice profile.

        Returns:
            Profile dict if found, None if not found.

        Raises:
            STTDConnectionError: If unable to connect to server.
            STTDError: If request fails.
        """
        try:
            response = self._client.get(f"{self.base_url}/profiles/{name}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise STTDConnectionError(f"Cannot connect to STTD server at {self.base_url}: {e}")
        except httpx.RequestError as e:
            raise STTDError(f"Request error: {e}")

    def create_profile(self, name: str, audio_path: Path) -> dict:
        """Create a voice profile from audio file.

        Args:
            name: Name for the voice profile.
            audio_path: Path to the audio file containing voice sample.

        Returns:
            Created profile dict.

        Raises:
            STTDConnectionError: If unable to connect to server.
            STTDError: If request fails.
            FileNotFoundError: If audio file doesn't exist.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        content_type = self._get_content_type(audio_path)

        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            response = self._client.post(
                f"{self.base_url}/profiles/{name}",
                content=audio_data,
                headers={"Content-Type": content_type},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise STTDConnectionError(f"Cannot connect to STTD server at {self.base_url}: {e}")
        except httpx.RequestError as e:
            raise STTDError(f"Request error: {e}")

    def delete_profile(self, name: str) -> bool:
        """Delete a voice profile.

        Args:
            name: Name of the voice profile to delete.

        Returns:
            True if deleted, False if profile not found.

        Raises:
            STTDConnectionError: If unable to connect to server.
            STTDError: If request fails.
        """
        try:
            response = self._client.delete(f"{self.base_url}/profiles/{name}")
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
        except httpx.ConnectError as e:
            raise STTDConnectionError(f"Cannot connect to STTD server at {self.base_url}: {e}")
        except httpx.RequestError as e:
            raise STTDError(f"Request error: {e}")

    def _get_content_type(self, audio_path: Path) -> str:
        """Get MIME content type for audio file.

        Args:
            audio_path: Path to audio file.

        Returns:
            MIME content type string.
        """
        suffix = audio_path.suffix.lower()
        content_types = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".m4a": "audio/mp4",
            ".flac": "audio/flac",
            ".ogg": "audio/ogg",
            ".webm": "audio/webm",
        }
        return content_types.get(suffix, "audio/wav")


# Singleton client instance using config
_client: STTDClient | None = None


def get_sttd_client() -> STTDClient:
    """Get or create the global STTD client instance.

    Returns:
        STTDClient configured from global config.
    """
    global _client
    if _client is None:
        from src.config import config

        _client = STTDClient(
            host=config.sttd.host,
            port=config.sttd.port,
            timeout=config.sttd.timeout,
        )
    return _client


def reset_sttd_client() -> None:
    """Reset the global STTD client (useful for config changes)."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
