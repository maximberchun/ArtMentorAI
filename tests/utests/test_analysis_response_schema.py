"""Unit tests for the structured analysis response contract."""

from __future__ import annotations

import pytest

from ule.artmentorai_project.models.responses.analysis_response import AnalysisResponse


def test_analysis_response_accepts_structured_contract_payload() -> None:
    """The new schema should validate a full structured critique payload."""
    response = AnalysisResponse(
        score=9,
        rubric_anchors=['Confident perspective block-in'],
        prioritized_issues=[
            {
                'title': 'Minor hand proportion mismatch',
                'diagnosis': 'The right hand reads slightly oversized versus forearm length.',
                'priority': 1,
            }
        ],
        root_causes=['Final measurement pass was skipped'],
        targeted_drills=[
            {
                'name': 'Hand-to-forearm ratio pass',
                'objective': 'Measure hand length against forearm landmarks.',
                'success_check': 'Hand length stays consistent across 10 studies.',
            }
        ],
        readiness_gate='Proceed to stylization after proportional construction stays consistent.',
        confidence=0.88,
    )

    assert response.score == 9
    assert response.prioritized_issues[0].title == 'Minor hand proportion mismatch'


def test_analysis_response_rejects_confidence_outside_range() -> None:
    """Confidence should remain normalized between 0 and 1."""
    with pytest.raises(ValueError, match='less than or equal to 1'):
        AnalysisResponse(
            score=6,
            rubric_anchors=[],
            prioritized_issues=[],
            root_causes=[],
            targeted_drills=[],
            readiness_gate='Fix core form before moving to detail.',
            confidence=1.2,
        )
