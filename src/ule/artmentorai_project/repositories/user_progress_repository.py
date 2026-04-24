"""Repository for ``public.user_progress``."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import Client

from ..models.db_rows import UserProgressRow
from ._rows import as_model, as_model_list, single_row_dict

XP_PER_SCORE_POINT = 10
XP_PER_LEVEL = 250


class UserProgressRepository:
    """Maintain private progression values for each user."""

    _table = 'user_progress'

    def __init__(self, client: Client, logger: logging.Logger | None = None) -> None:
        self._client = client
        self._logger = logger or logging.getLogger(__name__)

    def get(self, user_id: str) -> UserProgressRow | None:
        """Get user progress row by user id."""
        try:
            response = (
                self._client.table(self._table).select('*').eq('user_id', user_id).limit(1).execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to load user_progress user_id=%s', user_id)
            msg = f'Failed to load user progress: {exc!s}'
            raise RuntimeError(msg) from exc

        rows = as_model_list(UserProgressRow, response.data)
        return rows[0] if rows else None

    def upsert_after_critique(self, *, user_id: str, score: int) -> UserProgressRow:
        """Increment XP/level/streak for one completed critique."""
        existing = self.get(user_id)
        today = datetime.now(tz=UTC).date()
        gained_xp = max(1, score) * XP_PER_SCORE_POINT

        if existing is None:
            total_xp = gained_xp
            streak_count = 1
            last_date = today
            badges: list[str] = []
        else:
            total_xp = existing.total_xp + gained_xp
            badges = existing.badges
            last_date = today
            if existing.streak_last_date == today:
                streak_count = existing.streak_count
            elif existing.streak_last_date == today - timedelta(days=1):
                streak_count = existing.streak_count + 1
            else:
                streak_count = 1

        payload = {
            'user_id': user_id,
            'total_xp': total_xp,
            'current_level': (total_xp // XP_PER_LEVEL) + 1,
            'streak_count': streak_count,
            'streak_last_date': last_date.isoformat(),
            'badges': badges,
        }
        try:
            self._client.table(self._table).upsert(payload, on_conflict='user_id').execute()
        except Exception as exc:
            self._logger.exception('Failed to upsert user_progress user_id=%s', user_id)
            msg = f'Failed to update user progress: {exc!s}'
            raise RuntimeError(msg) from exc

        refreshed = self.get(user_id)
        if refreshed is None:
            msg = 'Failed to reload user progress after upsert.'
            raise RuntimeError(msg)
        return refreshed

    def default(self, user_id: str) -> UserProgressRow:
        """Build default in-memory progress shape when user has no row yet."""
        return UserProgressRow(
            user_id=user_id,
            total_xp=0,
            current_level=1,
            streak_count=0,
            streak_last_date=None,
            badges=[],
        )
