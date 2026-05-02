"""Integration-style tests for analysis critique endpoint flows."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from ule.artmentorai_project.endpoints.analysis import create_analysis_router
from ule.artmentorai_project.models import AuthUser, ConversationChatResponse


@dataclass
class _DummyAnalysisResult:
    score: int
    rubric_anchors: list[str]
    prioritized_issues: list[dict[str, str | int]]
    root_causes: list[str]
    targeted_drills: list[dict[str, str]]
    readiness_gate: str
    confidence: float


class _FakeAgentService:
    def __init__(self, _config) -> None:
        self._result = _DummyAnalysisResult(
            score=7,
            rubric_anchors=['Strong gesture rhythm'],
            prioritized_issues=[
                {
                    'title': 'arm proportion mismatch',
                    'diagnosis': 'Forearm is proportionally too long.',
                    'priority': 1,
                }
            ],
            root_causes=['Landmark checks were skipped'],
            targeted_drills=[
                {
                    'name': 'Limb proportion block-in',
                    'objective': 'Match limb units before rendering details.',
                    'success_check': 'Arms stay within one head-length ratio tolerance.',
                }
            ],
            readiness_gate='Fix limb construction before anatomy detailing.',
            confidence=0.82,
        )

    async def analyze_image(self, **_kwargs):
        return self._result

    async def answer_conversation(self, **_kwargs):
        return ConversationChatResponse(
            reply=(
                'For fundamentals, many artists start with Betty Edwards or '
                'a basic perspective text; match the book to your medium and goals.'
            ),
        )


class _FakeProfileService:
    def __init__(self, config, logger) -> None:
        self._config = config
        self._logger = logger

    def get_profile(self, _user_id: str):
        return None


class _FailingVectorService:
    def search_similar_critiques(self, **_kwargs):
        raise RuntimeError('vector backend temporarily unavailable')

    def search_similar_portfolio_items(self, **_kwargs):
        return []

    def save_critique(self, *_args, **_kwargs):
        return 'point-id'

    def health_check(self) -> bool:
        return True


def _build_analysis_client(app_config, monkeypatch) -> TestClient:
    """Create test app with analysis router and all external dependencies mocked."""
    import ule.artmentorai_project.endpoints.analysis as analysis_module

    async def _verify_access_token(_self, token: str) -> AuthUser:
        if token == 'invalid-token':
            raise HTTPException(status_code=401, detail='Invalid authorization token')
        return AuthUser(user_id='user-42', email='artist@example.com', role='authenticated')

    monkeypatch.setattr(analysis_module, 'AgentService', _FakeAgentService)
    monkeypatch.setattr(analysis_module, 'ProfileService', _FakeProfileService)
    monkeypatch.setattr(analysis_module, 'get_vector_service', lambda _config: _FailingVectorService())
    monkeypatch.setattr(analysis_module, 'get_storage_service', lambda _config: None)
    monkeypatch.setattr(
        analysis_module,
        'create_sync_supabase_service_client',
        lambda _config: (_ for _ in ()).throw(RuntimeError('db unavailable')),
    )
    monkeypatch.setattr(
        'ule.artmentorai_project.services.auth_service.AuthService.verify_access_token',
        _verify_access_token,
    )

    app = FastAPI()
    app.include_router(create_analysis_router(app_config))
    return TestClient(app)


def test_critique_returns_success_when_memory_or_db_dependencies_fail(
    app_config,
    monkeypatch,
) -> None:
    """Endpoint should still return analysis when vector/db dependencies fail."""
    client = _build_analysis_client(app_config, monkeypatch)

    response = client.post(
        '/analysis/critique',
        data={'user_input': 'Please critique my composition and anatomy.'},
        headers={'Authorization': 'Bearer valid-token'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['score'] is None
    assert payload['prioritized_issues'][0]['title'] == 'arm proportion mismatch'
    assert payload['targeted_drills'][0]['name'] == 'Limb proportion block-in'


def test_critique_rejects_missing_inputs_with_422(app_config, monkeypatch) -> None:
    """Request without image or user text should fail validation."""
    client = _build_analysis_client(app_config, monkeypatch)

    response = client.post(
        '/analysis/critique',
        data={},
        headers={'Authorization': 'Bearer valid-token'},
    )

    assert response.status_code == 422
    assert response.json()['detail'] == 'Provide at least an image, a text comment, or both.'


def test_critique_rejects_invalid_token_with_401(app_config, monkeypatch) -> None:
    """Invalid bearer tokens should fail before endpoint logic executes."""
    client = _build_analysis_client(app_config, monkeypatch)

    response = client.post(
        '/analysis/critique',
        data={'user_input': 'Any feedback?'},
        headers={'Authorization': 'Bearer invalid-token'},
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid authorization token'


def test_chat_returns_reply_for_general_question(app_config, monkeypatch) -> None:
    """General Q&A should return a conversational reply without critique RAG."""
    client = _build_analysis_client(app_config, monkeypatch)

    response = client.post(
        '/analysis/chat',
        json={'message': 'What book do you recommend for learning drawing?'},
        headers={'Authorization': 'Bearer valid-token'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert 'reply' in payload
    assert 'Betty Edwards' in payload['reply']


def test_chat_rejects_critique_shaped_message_with_422(app_config, monkeypatch) -> None:
    """Critique-intent text should be directed to /analysis/critique, not /chat."""
    client = _build_analysis_client(app_config, monkeypatch)

    response = client.post(
        '/analysis/chat',
        json={'message': 'Please critique my anatomy study.'},
        headers={'Authorization': 'Bearer valid-token'},
    )

    assert response.status_code == 422
    assert 'artwork feedback' in response.json()['detail'].lower()
