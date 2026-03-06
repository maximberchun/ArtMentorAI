"""Service for managing user profiles (goals and preferences)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..models import UserProfile


class ProfileService:
    """Persistence layer for `UserProfile` objects.

    For the MVP this uses a simple JSON file on disk, keyed by ``user_id``.
    The storage format is a mapping::

        {
            "<user_id>": {
                "user_id": "...",
                "goals": [...],
                "preferred_styles": [...],
                "disliked_styles": [...],
                "favorite_artists": [...],
                "experience_level": "..."
            },
            ...
        }
    """

    def __init__(
        self,
        storage_path: str | Path = 'user_profiles.json',
        logger: logging.Logger | None = None,
    ) -> None:
        self._path = Path(storage_path)
        self._logger = logger or logging.getLogger(__name__)

    def _load_all(self) -> dict[str, dict[str, Any]]:
        """Load all profiles from disk, returning an empty mapping if missing."""
        if not self._path.exists():
            return {}

        try:
            raw = self._path.read_text(encoding='utf-8')
            if not raw.strip():
                return {}
            data = json.loads(raw)
            if not isinstance(data, dict):
                self._logger.warning(
                    'Profile storage file %s did not contain a JSON object; resetting.',
                    self._path,
                )
                return {}
            return {str(k): v for k, v in data.items()}
        except json.JSONDecodeError as e:
            self._logger.exception(
                'Failed to decode profile storage JSON at %s', self._path
            )
            msg = f'Corrupted profile storage at {self._path}: {e!s}'
            raise RuntimeError(msg) from e
        except OSError as e:
            self._logger.exception('Failed to read profile storage at %s', self._path)
            msg = f'Could not read profile storage at {self._path}: {e!s}'
            raise RuntimeError(msg) from e

    def _save_all(self, data: dict[str, dict[str, Any]]) -> None:
        """Persist all profiles atomically to disk."""
        try:
            self._path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
        except OSError as e:
            self._logger.exception('Failed to write profile storage to %s', self._path)
            msg = f'Could not write profile storage to {self._path}: {e!s}'
            raise RuntimeError(msg) from e

    def get_profile(self, user_id: str) -> UserProfile | None:
        """Return the profile for ``user_id`` or ``None`` if absent."""
        data = self._load_all()
        profile_data = data.get(user_id)
        if profile_data is None:
            return None
        return UserProfile.model_validate(profile_data)

    def upsert_profile(self, profile: UserProfile) -> UserProfile:
        """Create or update the profile for ``profile.user_id``."""
        data = self._load_all()
        data[profile.user_id] = profile.model_dump()
        self._save_all(data)
        self._logger.info('Saved profile for user_id=%s', profile.user_id)
        return profile


__all__ = [
    'ProfileService',
]

