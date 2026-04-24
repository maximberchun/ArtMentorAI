"""Service for managing user profiles (goals and preferences)."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..db import create_sync_supabase_service_client
from ..models import UserProfile
from ..repositories import ProfileRepository


class ProfileService:
    """Persistence layer for ``UserProfile`` objects backed by Supabase Postgres."""

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config
        self._logger = logger or logging.getLogger(__name__)

    def _repo(self) -> ProfileRepository:
        sb = create_sync_supabase_service_client(self._config)
        return ProfileRepository(sb, self._logger)

    def get_profile(self, user_id: str) -> UserProfile | None:
        """Return the profile for ``user_id`` or ``None`` if absent."""
        row = self._repo().get_active(user_id)
        if row is None:
            return None
        return UserProfile(
            user_id=row.user_id,
            goals=row.goals,
            preferred_styles=row.preferred_styles,
            disliked_styles=row.disliked_styles,
            favorite_artists=row.favorite_artists,
            experience_level=row.experience_level,
            retain_memory=row.retain_memory,
        )

    def upsert_profile(self, profile: UserProfile) -> UserProfile:
        """Create or update the profile for ``profile.user_id``."""
        row = self._repo().upsert(profile)
        self._logger.info('Saved profile for user_id=%s', profile.user_id)
        return UserProfile(
            user_id=row.user_id,
            goals=row.goals,
            preferred_styles=row.preferred_styles,
            disliked_styles=row.disliked_styles,
            favorite_artists=row.favorite_artists,
            experience_level=row.experience_level,
            retain_memory=row.retain_memory,
        )


__all__ = [
    'ProfileService',
]

