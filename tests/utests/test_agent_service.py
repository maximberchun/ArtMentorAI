"""Unit tests for agent service orchestration and error paths."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest
from pydantic_ai.exceptions import ModelHTTPError

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


class _GeminiConfigStub:
    model_name = 'gemini-test'

    def model_try_chain(self) -> tuple[str, ...]:
        return ('gemini-test',)


def _build_service(agent) -> AgentService:
    service = AgentService.__new__(AgentService)
    service.config = SimpleNamespace(
        gemini=_GeminiConfigStub(),
        web_search_enabled=False,
    )
    service.logger = logging.getLogger('tests.agent_service')
    service.agent = agent
    service._search_calls_used = 99
    service._model_run_timeout_seconds = 60.0
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


class _GeminiWithFallbackStub:
    model_name = 'gemini-primary'

    def model_try_chain(self) -> tuple[str, ...]:
        return ('gemini-primary', 'gemini-fallback')


class _AgentRaises503:
    async def run(self, _message):
        raise ModelHTTPError(503, 'gemini-primary', {})


def test_analyze_image_retries_with_fallback_model_on_503() -> None:
    """After HTTP 503 from the primary model, the next model in the chain should be used."""
    output_payload = {
        'score': 7,
        'rubric_anchors': ['Clean gesture rhythm'],
        'prioritized_issues': [
            {
                'title': 'Torso perspective drift',
                'diagnosis': 'Ribcage box rotates without a stable horizon reference.',
                'priority': 1,
            }
        ],
        'root_causes': ['Skipped construction lines'],
        'targeted_drills': [
            {
                'name': 'Box rotation sheet',
                'objective': 'Stabilize horizon handling in figure drawing.',
                'success_check': 'Eight of ten boxes read with coherent vanishing logic.',
            }
        ],
        'readiness_gate': 'Advance only after stable construction perspective.',
        'confidence': 0.8,
    }

    fallback_agent = _CapturingAgent(output_payload)
    service = AgentService.__new__(AgentService)
    service.config = SimpleNamespace(
        gemini=_GeminiWithFallbackStub(),
        web_search_enabled=False,
    )
    service.logger = logging.getLogger('tests.agent_service')
    service.agent = _AgentRaises503()
    service._search_calls_used = 99

    def _build_fallback(model: str) -> _CapturingAgent:
        assert model == 'gemini-fallback'
        return fallback_agent

    service._build_analysis_agent = _build_fallback  # type: ignore[method-assign]
    service._model_run_timeout_seconds = 60.0

    result = asyncio.run(
        service.analyze_image(
            image_bytes=b'fake-image',
            mime_type='image/png',
            user_input='test',
            has_artwork=True,
        )
    )

    assert isinstance(result, AnalysisResponse)
    assert result.score == 7
    assert service._search_calls_used == 0
    assert isinstance(fallback_agent.last_message, list)


def test_analyze_image_retries_with_fallback_model_on_client_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After asyncio wait_for TimeoutError on the primary, the next model should be used."""
    output_payload = {
        'score': 7,
        'rubric_anchors': ['Clean gesture rhythm'],
        'prioritized_issues': [
            {
                'title': 'Torso perspective drift',
                'diagnosis': 'Ribcage box rotates without a stable horizon reference.',
                'priority': 1,
            }
        ],
        'root_causes': ['Skipped construction lines'],
        'targeted_drills': [
            {
                'name': 'Box rotation sheet',
                'objective': 'Stabilize horizon handling in figure drawing.',
                'success_check': 'Eight of ten boxes read with coherent vanishing logic.',
            }
        ],
        'readiness_gate': 'Advance only after stable construction perspective.',
        'confidence': 0.8,
    }

    calls = {'n': 0}

    async def fake_wait_for(awaitable, timeout):
        calls['n'] += 1
        if calls['n'] == 1:
            if asyncio.iscoroutine(awaitable):
                awaitable.close()
            raise TimeoutError()
        return await awaitable

    monkeypatch.setattr(agent_module.asyncio, 'wait_for', fake_wait_for)

    fallback_agent = _CapturingAgent(output_payload)
    service = AgentService.__new__(AgentService)
    service.config = SimpleNamespace(
        gemini=_GeminiWithFallbackStub(),
        web_search_enabled=False,
    )
    service.logger = logging.getLogger('tests.agent_service')
    service.agent = _CapturingAgent(output_payload)  # primary: first wait_for fails before run
    service._search_calls_used = 99

    def _build_fallback(model: str) -> _CapturingAgent:
        assert model == 'gemini-fallback'
        return fallback_agent

    service._build_analysis_agent = _build_fallback  # type: ignore[method-assign]
    service._model_run_timeout_seconds = 60.0

    result = asyncio.run(
        service.analyze_image(
            image_bytes=b'fake-image',
            mime_type='image/png',
            user_input='test',
            has_artwork=True,
        )
    )

    assert isinstance(result, AnalysisResponse)
    assert result.score == 7
    assert calls['n'] == 2
    assert isinstance(fallback_agent.last_message, list)


def test_looks_incomplete_reply_detects_mid_sentence_cutoff() -> None:
    """Long responses that end without terminal punctuation should be treated as incomplete."""
    service = _build_service(_CapturingAgent({'reply': 'unused'}))
    incomplete = 'This is a fairly long answer that keeps explaining drawing fundamentals and practice'
    incomplete = f'{incomplete} methods and recommended resources for beginners'
    assert service._looks_incomplete_reply(incomplete)
    assert not service._looks_incomplete_reply('Short reply.')


def test_answer_conversation_requests_one_continuation_when_reply_looks_truncated() -> None:
    """Chat flow should request one continuation pass for abruptly cut responses."""

    primary_reply = {
        'reply': (
            'Learning to draw starts with line, shape, value, and perspective. '
            'Practice 20 minutes daily with gesture and simple still lifes'
        ),
        'analysis': None,
    }
    continuation_reply = {
        'reply': 'Then study composition and anatomy in small focused drills.',
        'analysis': None,
    }
    calls: list[str] = []

    async def _fake_run_with_fallback(*, message, primary_agent, build_for_model, op_name):  # noqa: ANN001
        calls.append(op_name)
        if len(calls) == 1:
            return _FakeRunResult(primary_reply)
        assert 'PARTIAL PREVIOUS REPLY' in message
        return _FakeRunResult(continuation_reply)

    service = AgentService.__new__(AgentService)
    service.config = SimpleNamespace(
        gemini=_GeminiConfigStub(),
        web_search_enabled=False,
    )
    service.logger = logging.getLogger('tests.agent_service')
    service.chat_agent = object()
    service._build_chat_agent = lambda _model: object()  # type: ignore[method-assign]
    service._run_agent_with_model_fallback = _fake_run_with_fallback  # type: ignore[method-assign]
    service._search_calls_used = 0
    service._model_run_timeout_seconds = 60.0

    result = asyncio.run(
        service.answer_conversation(
            user_input='How do I learn to draw?',
            profile_context=None,
            conversation_context=None,
        )
    )

    assert calls == ['conversation chat', 'conversation chat continuation']
    assert 'Then study composition and anatomy' in result.reply
