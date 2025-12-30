"""Voice profile management service.

Note: Voice profile embedding/registration is now handled by the STTD server.
This service stores audio samples locally for reference and metadata.
"""

import logging
from datetime import datetime
from typing import Any

from src.config import config
from src.storage.db import Database
from src.storage.models import SpeakerProfile

logger = logging.getLogger(__name__)


class VoiceProfileService:
    """Service for managing voice profiles (audio sample storage)."""

    def __init__(self, db_path: str = None):
        """Initialize voice profile service.

        Args:
            db_path: Path to database file
        """
        self.db_path = db_path or config.database.path
        self._db = None

    @property
    def db(self) -> Database:
        """Get database connection (lazy initialization)."""
        if self._db is None:
            self._db = Database(db_path=self.db_path)
            self._db.connect()
        return self._db

    def register_from_file(
        self,
        name: str,
        audio_data: bytes,
        display_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SpeakerProfile:
        """Register a new voice profile from audio file data.

        The audio sample is stored locally. The STTD server handles
        speaker diarization and identification during transcription.

        Args:
            name: Unique identifier for the profile (e.g., 'alice', 'bob')
            audio_data: Raw audio bytes (WAV, MP3, etc.)
            display_name: Human-readable name
            metadata: Additional profile metadata

        Returns:
            Created SpeakerProfile

        Raises:
            ValueError: If profile name already exists
        """
        # Normalize name
        name = name.lower().replace(" ", "_")

        # Check if profile already exists
        existing = self.db.get_speaker_profile_by_name(name)
        if existing:
            raise ValueError(f"Profile with name '{name}' already exists")

        # Create profile in database (audio sample stored for reference)
        now = datetime.utcnow()
        profile = SpeakerProfile(
            name=name,
            display_name=display_name or name.title().replace("_", " "),
            audio_sample=audio_data,
            embedding_data=None,  # Embedding handled by STTD server
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        profile_id = self.db.create_speaker_profile(profile)
        profile.profile_id = profile_id

        logger.info(f"Created voice profile {profile_id} for '{name}'")
        return profile

    def list_profiles(self) -> list[SpeakerProfile]:
        """List all registered voice profiles.

        Returns:
            List of SpeakerProfile objects
        """
        return self.db.get_speaker_profiles()

    def get_profile(self, profile_id: int) -> SpeakerProfile | None:
        """Get a specific profile by ID.

        Args:
            profile_id: Profile identifier

        Returns:
            SpeakerProfile if found, None otherwise
        """
        return self.db.get_speaker_profile(profile_id)

    def get_profile_by_name(self, name: str) -> SpeakerProfile | None:
        """Get a profile by name.

        Args:
            name: Profile name

        Returns:
            SpeakerProfile if found, None otherwise
        """
        return self.db.get_speaker_profile_by_name(name.lower())

    def delete_profile(self, profile_id: int) -> bool:
        """Delete a voice profile.

        Args:
            profile_id: ID of profile to delete

        Returns:
            True if deleted, False if not found
        """
        profile = self.db.get_speaker_profile(profile_id)
        if not profile:
            return False

        result = self.db.delete_speaker_profile(profile_id)
        if result:
            logger.info(f"Deleted voice profile {profile_id} ('{profile.name}')")
        return result

    def update_profile(
        self,
        profile_id: int,
        display_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update a voice profile.

        Args:
            profile_id: ID of profile to update
            display_name: New display name
            metadata: New metadata

        Returns:
            True if updated, False if not found
        """
        updates = {}
        if display_name is not None:
            updates["display_name"] = display_name
        if metadata is not None:
            updates["metadata"] = metadata

        if not updates:
            return False

        return self.db.update_speaker_profile(profile_id, updates)

    def get_profile_count(self) -> int:
        """Get the total number of registered profiles.

        Returns:
            Number of profiles
        """
        return len(self.db.get_speaker_profiles())

    def close(self):
        """Close database connection."""
        if self._db:
            self._db.disconnect()
            self._db = None


# Singleton instance
_voice_profile_service: VoiceProfileService | None = None


def get_voice_profile_service() -> VoiceProfileService:
    """Get the voice profile service singleton."""
    global _voice_profile_service
    if _voice_profile_service is None:
        _voice_profile_service = VoiceProfileService()
    return _voice_profile_service
