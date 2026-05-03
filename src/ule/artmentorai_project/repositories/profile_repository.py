"""Repository for ``public.profiles``."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

    from ..models import UserProfile

from ..models.db_rows import ProfileRow
from ._rows import as_model_list, postgrest_returned_rows


class ProfileRepository:
    """CRUD-style access to user profiles (privacy + soft delete)."""

    _table = 'profiles'

    def __init__(self, client: Client, logger: logging.Logger | None = None) -> None:
        self._client = client
        self._logger = logger or logging.getLogger(__name__)

    def get_active(self, user_id: str) -> ProfileRow | None:
        """Return the non-deleted profile for ``user_id``, if any."""
        try:
            response = (
                self._client.table(self._table)
                .select('*')
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to load profile user_id=%s', user_id)
            msg = f'Failed to load profile: {exc!s}'
            raise RuntimeError(msg) from exc

        rows = as_model_list(ProfileRow, response.data)
        return rows[0] if rows else None

    def upsert(self, profile: UserProfile) -> ProfileRow:
        """Create or update a profile and clear ``deleted_at`` if it was soft-deleted."""
        payload: dict[str, Any] = {
            'user_id': profile.user_id,
            'goals': profile.goals,
            'preferred_styles': profile.preferred_styles,
            'disliked_styles': profile.disliked_styles,
            'favorite_artists': profile.favorite_artists,
            'experience_level': profile.experience_level,
            'retain_memory': profile.retain_memory,
            'deleted_at': None,
        }
        try:
            self._client.table(self._table).upsert(payload, on_conflict='user_id').execute()
        except Exception as exc:
            self._logger.exception('Failed to upsert profile user_id=%s', profile.user_id)
            msg = f'Failed to save profile: {exc!s}'
            raise RuntimeError(msg) from exc

        row = self.get_active(profile.user_id)
        if row is None:
            msg = 'Failed to reload profile after upsert.'
            raise RuntimeError(msg)
        return row

    def soft_delete(self, user_id: str) -> bool:
        """Mark the profile as deleted. Returns whether a row was updated."""
        stamp = datetime.now(tz=UTC).isoformat()
        try:
            response = (
                self._client.table(self._table)
                .update({'deleted_at': stamp})
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .select('user_id')
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to soft-delete profile user_id=%s', user_id)
            msg = f'Failed to delete profile: {exc!s}'
            raise RuntimeError(msg) from exc

        return postgrest_returned_rows(response.data)
