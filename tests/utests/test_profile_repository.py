"""Unit tests for profile repository boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ule.artmentorai_project.repositories.profile_repository import ProfileRepository


def test_profile_get_active_raises_on_invalid_supabase_response_shape() -> None:
    """Repository should fail fast when Supabase returns non-list query payloads."""
    client = MagicMock()
    repo = ProfileRepository(client)
    (
        client.table.return_value.select.return_value.eq.return_value.is_.return_value.limit.return_value.execute.return_value
    ) = SimpleNamespace(data='not-a-list')

    with pytest.raises(TypeError, match='Supabase data must be a list'):
        repo.get_active('user-1')


def test_profile_soft_delete_returns_false_when_no_rows_updated() -> None:
    """Soft delete should report False when update returns an empty list."""
    client = MagicMock()
    repo = ProfileRepository(client)
    (
        client.table.return_value.update.return_value.eq.return_value.is_.return_value.select.return_value.execute.return_value
    ) = SimpleNamespace(data=[])

    deleted = repo.soft_delete('user-1')

    assert deleted is False
