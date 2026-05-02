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


def test_critique_create_persists_structured_fields() -> None:
    """Create should send structured critique payload fields to Supabase."""
    client = MagicMock()
    repo = CritiqueRepository(client)

    execute_mock = (
        client.table.return_value.insert.return_value.execute
    )
    execute_mock.return_value = MagicMock(
        data=[
            {
                'id': 'crit-1',
                'user_id': 'user-1',
                'summary': 'Perspective drift in torso construction.',
                'score': 7,
                'rubric_anchors': ['Good gesture rhythm'],
                'prioritized_issues': [
                    {
                        'title': 'Torso perspective drift',
                        'diagnosis': 'Torso box rotates off horizon.',
                        'priority': 1,
                    }
                ],
                'root_causes': ['Skipped construction pass'],
                'targeted_drills': [
                    {
                        'name': 'Torso box rotation sheet',
                        'objective': 'Align box planes to a shared horizon.',
                        'success_check': '8/10 coherent boxes.',
                    }
                ],
                'readiness_gate': 'Stabilize construction before anatomy detail.',
                'confidence': 0.83,
                'tags': [],
                'goals_snapshot': None,
                'vector_point_id': None,
            }
        ]
    )

    repo.create(
        user_id='user-1',
        summary='Perspective drift in torso construction.',
        score=7,
        rubric_anchors=['Good gesture rhythm'],
        prioritized_issues=[
            {
                'title': 'Torso perspective drift',
                'diagnosis': 'Torso box rotates off horizon.',
                'priority': 1,
            }
        ],
        root_causes=['Skipped construction pass'],
        targeted_drills=[
            {
                'name': 'Torso box rotation sheet',
                'objective': 'Align box planes to a shared horizon.',
                'success_check': '8/10 coherent boxes.',
            }
        ],
        readiness_gate='Stabilize construction before anatomy detail.',
        confidence=0.83,
    )

    payload = client.table.return_value.insert.call_args.args[0]
    assert 'prioritized_issues' in payload
    assert 'targeted_drills' in payload
    assert payload['readiness_gate'] == 'Stabilize construction before anatomy detail.'
