"""Unit tests for vector sync worker critique mappings."""

from __future__ import annotations

from ule.artmentorai_project.models.db_rows import CritiqueRow
from ule.artmentorai_project.services.vector_sync_worker import _critique_from_row


def test_critique_from_row_maps_structured_issue_and_drill_fields() -> None:
    """Worker should map stored structured critique fields to vector model."""
    row = CritiqueRow(
        id='crit-1',
        user_id='user-1',
        summary='Perspective consistency issues in torso construction.',
        score=7,
        rubric_anchors=['Good gesture rhythm'],
        prioritized_issues=[
            {
                'title': 'Torso perspective drift',
                'diagnosis': 'Torso box rotates off shared horizon.',
                'priority': 1,
            }
        ],
        root_causes=['Construction pass skipped'],
        targeted_drills=[
            {
                'name': 'Torso box rotation sheet',
                'objective': 'Align planes to one horizon.',
                'success_check': '8/10 coherent boxes.',
            }
        ],
        readiness_gate='Stabilize construction before anatomy detail.',
    )

    critique = _critique_from_row(row)

    assert critique.prioritized_issues == ['Torso perspective drift']
    assert critique.readiness_gate == 'Stabilize construction before anatomy detail.'
    assert 'Torso box rotation sheet' in critique.drill_notes
