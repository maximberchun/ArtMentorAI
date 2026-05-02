"""Unit tests for agent service orchestration and error paths."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest

from ule.artmentorai_project.exceptions import AIServiceError
from ule.artmentorai_project.models.responses.analysis_response import AnalysisResponse
from ule.artmentorai_project.services import agent_service as agent_module
from ule.artmentorai_project.services.agent_service import AgentService


class _FakeRunResult:
    def __init__(self, output) -> None:
        self.output = output


class _CapturingAgent:
    def __init__(self, output) -> None:
        self.output = output
        self.last_message = None

    async def run(self, message):
        self.last_message = message
        return _FakeRunResult(self.output)


def _build_service(agent) -> AgentService:
    service = AgentService.__new__(AgentService)
    service.config = SimpleNamespace(
        gemini=SimpleNamespace(model_name='gemini-test'),
        web_search_enabled=False,
    )
    service.logger = logging.getLogger('tests.agent_service')
    service.agent = agent
    service._search_calls_used = 99
    return service


def test_analyze_image_normalizes_dict_output_and_attaches_image() -> None:
    """Analyze flow should normalize dict output and include binary image content."""
    output_payload = {
        'score': 7,
        'rubric_anchors': ['Clean gesture rhythm', 'Perspective drift in torso box'],
        'prioritized_issues': [
            {
                'title': 'Torso perspective drift',
                'diagnosis': 'Ribcage box rotates without a stable horizon.',
                'priority': 1,
            }
        ],
        'root_causes': ['Skipped construction lines'],
        'targeted_drills': [
            {
                'name': 'Box rotation sheet',
                'objective': 'Stabilize horizon handling.',
                'success_check': '8/10 coherent boxes.',
            }
        ],
        'readiness_gate': 'Advance only after stable construction perspective.',
        'confidence': 0.84,
    }
    agent = _CapturingAgent(output_payload)
    service = _build_service(agent)

    result = asyncio.run(
        service.analyze_image(
            image_bytes=b'fake-image',
            mime_type='image/png',
            user_input='I need perspective feedback',
            has_artwork=True,
        )
    )

    assert isinstance(result, AnalysisResponse)
    assert result.score == 7
    assert service._search_calls_used == 0
    assert isinstance(agent.last_message, list)
    assert len(agent.last_message) == 2
    assert 'USER COMMENT' in agent.last_message[0]
    assert getattr(agent.last_message[1], 'media_type', None) == 'image/png'


def test_analyze_image_maps_timeout_to_ai_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeouts should be surfaced with a stable service-level error code."""

    class _AgentWithoutCoroutine:
        def run(self, _message):
            return object()

    async def _raise_timeout(_awaitable, timeout):
        raise TimeoutError()

    service = _build_service(_AgentWithoutCoroutine())
    monkeypatch.setattr(agent_module.asyncio, 'wait_for', _raise_timeout)

    with pytest.raises(AIServiceError, match='timed out') as exc:
        asyncio.run(service.analyze_image(user_input='test', has_artwork=False))

    assert exc.value.error_code == 'TIMEOUT'


def test_analyze_image_maps_quota_errors_with_retry_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """429 model errors should map to quota-exceeded service errors."""

    class _FakeModelHTTPError(Exception):
        def __init__(self, message: str, status_code: int, body: dict) -> None:
            super().__init__(message)
            self.message = message
            self.status_code = status_code
            self.body = body

    async def _raise_quota(_awaitable, timeout):
        raise _FakeModelHTTPError(
            message='quota',
            status_code=429,
            body={
                'details': [
                    {
                        '@type': 'type.googleapis.com/google.rpc.RetryInfo',
                        'retryDelay': '2s',
                    }
                ]
            },
        )

    class _AgentWithoutCoroutine:
        def run(self, _message):
            return object()

    service = _build_service(_AgentWithoutCoroutine())
    monkeypatch.setattr(agent_module, 'ModelHTTPError', _FakeModelHTTPError)
    monkeypatch.setattr(agent_module.asyncio, 'wait_for', _raise_quota)

    with pytest.raises(AIServiceError, match='quota exceeded') as exc:
        asyncio.run(service.analyze_image(user_input='test', has_artwork=False))

    assert exc.value.error_code == 'QUOTA_EXCEEDED'
    assert exc.value.retry_after == 2.0


def test_analyze_image_normalizes_issue_and_drill_order_by_dependency() -> None:
    """Out-of-order suggestions should be normalized to fundamentals-first sequence."""
    output_payload = {
        'score': 6,
        'rubric_anchors': ['Readable silhouette but unstable perspective'],
        'prioritized_issues': [
            {
                'title': 'Anatomy over-definition',
                'diagnosis': 'Muscle rendering is refined before construction is stable.',
                'priority': 1,
            },
            {
                'title': 'Perspective drift in torso box',
                'diagnosis': 'Torso box vanishing direction changes across the pose.',
                'priority': 2,
            },
            {
                'title': 'Construction breakdown in major forms',
                'diagnosis': 'Primary form volumes collapse during block in.',
                'priority': 3,
            },
        ],
        'root_causes': ['Detail pass started before core structure checks'],
        'targeted_drills': [
            {
                'name': 'Anatomy landmark polish pass',
                'objective': 'Refine landmark placement with surface detail.',
                'success_check': 'Landmarks read clearly during rendering.',
            },
            {
                'name': 'Perspective box sheet',
                'objective': 'Keep vanishing direction consistent for torso forms.',
                'success_check': '8 out of 10 boxes converge to coherent points.',
            },
            {
                'name': 'Construction gesture block-in set',
                'objective': 'Build stable form volumes before detail.',
                'success_check': 'Major forms remain readable after line cleanup.',
            },
        ],
        'readiness_gate': 'Do not advance until construction and perspective are stable.',
        'confidence': 0.81,
    }
    service = _build_service(_CapturingAgent(output_payload))

    result = asyncio.run(service.analyze_image(user_input='Check my workflow', has_artwork=True))

    assert [issue.title for issue in result.prioritized_issues] == [
        'Construction breakdown in major forms',
        'Perspective drift in torso box',
        'Anatomy over-definition',
    ]
    assert [issue.priority for issue in result.prioritized_issues] == [1, 2, 3]
    assert [drill.name for drill in result.targeted_drills] == [
        'Construction gesture block-in set',
        'Perspective box sheet',
        'Anatomy landmark polish pass',
    ]
