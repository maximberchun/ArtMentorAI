"""Unit tests for progress snapshot repository boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ule.artmentorai_project.repositories.progress_snapshot_repository import (
    ProgressSnapshotRepository,
)


def test_progress_snapshot_create_rejects_multi_row_insert_payload() -> None:
    """Progress snapshot create should fail if insert response shape is not single-row."""
    client = MagicMock()
    repo = ProgressSnapshotRepository(client)
    client.table.return_value.insert.return_value.execute.return_value = SimpleNamespace(
        data=[{'id': 'a'}, {'id': 'b'}]
    )

    with pytest.raises(RuntimeError, match='Expected exactly one Supabase row, got 2'):
        repo.create(user_id='user-1', rubric_key='composition')
