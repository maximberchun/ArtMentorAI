"""Unit tests for user progress repository boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ule.artmentorai_project.repositories.user_progress_repository import UserProgressRepository


def test_user_progress_upsert_after_critique_builds_expected_payload() -> None:
    """Upsert should compute XP, level and streak for first-time critique progress."""
    client = MagicMock()
    repo = UserProgressRepository(client)
    refreshed_row = SimpleNamespace(user_id='user-1', total_xp=70, current_level=1, streak_count=1)
    repo.get = MagicMock(side_effect=[None, refreshed_row])

    result = repo.upsert_after_critique(user_id='user-1', score=7)

    assert result is refreshed_row
    payload = client.table.return_value.upsert.call_args.args[0]
    assert payload['total_xp'] == 70
    assert payload['current_level'] == 1
    assert payload['streak_count'] == 1


def test_user_progress_upsert_after_critique_wraps_upsert_failure() -> None:
    """Upsert should wrap Supabase failures in stable repository RuntimeError."""
    client = MagicMock()
    repo = UserProgressRepository(client)
    repo.get = MagicMock(return_value=None)
    client.table.return_value.upsert.return_value.execute.side_effect = Exception('db timeout')

    with pytest.raises(RuntimeError, match='Failed to update user progress'):
        repo.upsert_after_critique(user_id='user-1', score=5)
