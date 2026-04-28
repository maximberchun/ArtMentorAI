"""Unit tests for critique repository boundaries."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ule.artmentorai_project.repositories.critique_repository import CritiqueRepository


def test_critique_set_vector_point_id_wraps_update_failure() -> None:
    """Critique repository should normalize vector-link update failures."""
    client = MagicMock()
    repo = CritiqueRepository(client)
    (
        client.table.return_value.update.return_value.eq.return_value.eq.return_value.is_.return_value.execute.side_effect
    ) = Exception('update failed')

    with pytest.raises(RuntimeError, match='Failed to update critique vector id'):
        repo.set_vector_point_id('crit-1', 'user-1', 'vec-1')
