"""Unit tests for analysis endpoint helper formatters."""

from __future__ import annotations

from ule.artmentorai_project.endpoints.analysis import (
    _build_assistant_conversation_message,
    _build_persistence_advice,
    _build_persistence_summary,
)
from ule.artmentorai_project.models.responses.analysis_response import AnalysisResponse


def _sample_response() -> AnalysisResponse:
    return AnalysisResponse(
        score=7,
        rubric_anchors=['Good gesture clarity'],
        prioritized_issues=[
            {
                'title': 'Torso perspective drift',
                'diagnosis': 'Ribcage box rotates without consistent vanishing direction.',
                'priority': 1,
            }
        ],
        root_causes=['Construction lines omitted in final pass'],
        targeted_drills=[
            {
                'name': 'Torso box rotation sheet',
                'objective': 'Align box planes with a shared horizon.',
                'success_check': '8/10 boxes keep coherent perspective alignment.',
            }
        ],
        readiness_gate='Stabilize form construction before anatomy refinement.',
        confidence=0.81,
    )


def test_persistence_helpers_flatten_structured_analysis_fields() -> None:
    """Persistence helper text should capture ordered issues and drills."""
    analysis = _sample_response()

    summary = _build_persistence_summary(analysis)
    advice = _build_persistence_advice(analysis)

    assert 'Torso perspective drift' in summary
    assert 'Torso box rotation sheet' in advice
    assert 'Gate:' in advice


def test_conversation_message_contains_new_schema_highlights() -> None:
    """Conversation memory format should include new pedagogical fields."""
    analysis = _sample_response()

    message = _build_assistant_conversation_message(analysis)

    assert 'Prioritized issues:' in message
    assert 'Readiness gate:' in message
