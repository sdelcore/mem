"""Voice profile management service."""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.config import config
from src.storage.db import Database
from src.storage.models import SpeakerProfile

logger = logging.getLogger(__name__)

# Try to import sttd ProfileManager
try:
    from sttd import ProfileManager

    STTD_AVAILABLE = True
except ImportError:
    logger.warning("sttd not available for voice profile management")
    STTD_AVAILABLE = False
    ProfileManager = None


class VoiceProfileService:
    """Service for managing voice profiles."""

    def __init__(self, db_path: str = None):
        """
        Initialize voice profile service.

        Args:
            db_path: Path to database file
        """
        self.db_path = db_path or config.database.path
        self.profiles_path = Path(config.sttd.profiles_path)
        self.profiles_path.mkdir(parents=True, exist_ok=True)

        self._profile_manager = None
        self._db = None

    @property
    def db(self) -> Database:
        """Get database connection (lazy initialization)."""
        if self._db is None:
            self._db = Database(db_path=self.db_path)
            self._db.connect()
        return self._db

    @property
    def profile_manager(self) -> Optional["ProfileManager"]:
        """Get sttd profile manager (lazy initialization)."""
        if self._profile_manager is None and STTD_AVAILABLE:
            self._profile_manager = ProfileManager(str(self.profiles_path))
        return self._profile_manager

    def register_from_file(
        self,
        name: str,
        audio_data: bytes,
        display_name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> SpeakerProfile:
        """
        Register a new voice profile from audio file data.

        Args:
            name: Unique identifier for the profile (e.g., 'alice', 'bob')
            audio_data: Raw audio bytes (WAV, MP3, etc.)
            display_name: Human-readable name
            metadata: Additional profile metadata

        Returns:
            Created SpeakerProfile

        Raises:
            ValueError: If profile name already exists or audio is invalid
        """
        # Normalize name
        name = name.lower().replace(" ", "_")

        # Check if profile already exists
        existing = self.db.get_speaker_profile_by_name(name)
        if existing:
            raise ValueError(f"Profile with name '{name}' already exists")

        # Save audio to temp file for sttd processing
        with tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False
        ) as tmp:
            tmp.write(audio_data)
            tmp_path = Path(tmp.name)

        try:
            # Use sttd ProfileManager to create embedding
            embedding_data = None
            if self.profile_manager:
                try:
                    self.profile_manager.register(name, str(tmp_path))
                    logger.info(f"Registered voice profile '{name}' with sttd")
                except Exception as e:
                    logger.warning(f"Failed to register with sttd: {e}")

            # Create profile in database
            now = datetime.utcnow()
            profile = SpeakerProfile(
                name=name,
                display_name=display_name or name.title().replace("_", " "),
                audio_sample=audio_data,
                embedding_data=embedding_data,
                metadata=metadata or {},
                created_at=now,
                updated_at=now,
            )

            profile_id = self.db.create_speaker_profile(profile)
            profile.profile_id = profile_id

            logger.info(f"Created voice profile {profile_id} for '{name}'")
            return profile

        finally:
            # Clean up temp file
            if tmp_path.exists():
                tmp_path.unlink()

    def list_profiles(self) -> list[SpeakerProfile]:
        """
        List all registered voice profiles.

        Returns:
            List of SpeakerProfile objects
        """
        return self.db.get_speaker_profiles()

    def get_profile(self, profile_id: int) -> Optional[SpeakerProfile]:
        """
        Get a specific profile by ID.

        Args:
            profile_id: Profile identifier

        Returns:
            SpeakerProfile if found, None otherwise
        """
        return self.db.get_speaker_profile(profile_id)

    def get_profile_by_name(self, name: str) -> Optional[SpeakerProfile]:
        """
        Get a profile by name.

        Args:
            name: Profile name

        Returns:
            SpeakerProfile if found, None otherwise
        """
        return self.db.get_speaker_profile_by_name(name.lower())

    def delete_profile(self, profile_id: int) -> bool:
        """
        Delete a voice profile.

        Args:
            profile_id: ID of profile to delete

        Returns:
            True if deleted, False if not found
        """
        # Get profile to find name
        profile = self.db.get_speaker_profile(profile_id)
        if not profile:
            return False

        # Remove from sttd profiles if available
        if self.profile_manager:
            try:
                self.profile_manager.delete(profile.name)
                logger.info(f"Removed profile '{profile.name}' from sttd")
            except Exception as e:
                logger.warning(f"Failed to remove from sttd: {e}")

        # Delete from database
        return self.db.delete_speaker_profile(profile_id)

    def update_profile(
        self,
        profile_id: int,
        display_name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Update a voice profile.

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
        """
        Get the total number of registered profiles.

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
_voice_profile_service: Optional[VoiceProfileService] = None


def get_voice_profile_service() -> VoiceProfileService:
    """Get the voice profile service singleton."""
    global _voice_profile_service
    if _voice_profile_service is None:
        _voice_profile_service = VoiceProfileService()
    return _voice_profile_service
