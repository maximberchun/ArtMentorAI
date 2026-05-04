"""Integration tests for auth, profile, portfolio, and progress endpoints."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from tests.conftest import create_test_limiter, install_slowapi
from ule.artmentorai_project.endpoints.auth import create_auth_router
from ule.artmentorai_project.endpoints.portfolio import create_portfolio_router
from ule.artmentorai_project.endpoints.profile import create_profile_router
from ule.artmentorai_project.endpoints.progress import create_progress_router
from ule.artmentorai_project.models import AuthUser


@pytest.fixture
def authenticated_user() -> AuthUser:
    """Canonical authenticated user returned by token verification stubs."""
    return AuthUser(user_id='user-123', email='artist@example.com', role='authenticated')


@pytest.fixture
def token_auth_stub(monkeypatch: pytest.MonkeyPatch, authenticated_user: AuthUser) -> None:
    """Stub token verification for all tested endpoint modules."""

    async def _verify_access_token(_self, token: str) -> AuthUser:
        if token == 'invalid-token':
            raise HTTPException(status_code=401, detail='Invalid authorization token')
        return authenticated_user

    monkeypatch.setattr(
        'ule.artmentorai_project.services.auth_service.AuthService.verify_access_token',
        _verify_access_token,
    )


def test_auth_me_returns_identity_when_token_is_valid(
    app_config,
    token_auth_stub,
    authenticated_user: AuthUser,
) -> None:
    """`/auth/me` returns user identity for valid bearer token."""
    app = FastAPI()
    app.include_router(create_auth_router(app_config))
    client = TestClient(app)

    response = client.get('/auth/me', headers={'Authorization': 'Bearer valid-token'})

    assert response.status_code == 200
    assert response.json() == authenticated_user.model_dump()


def test_auth_me_rejects_invalid_or_missing_token(app_config, token_auth_stub) -> None:
    """`/auth/me` returns 401 for invalid and missing auth credentials."""
    app = FastAPI()
    app.include_router(create_auth_router(app_config))
    client = TestClient(app)

    invalid_response = client.get('/auth/me', headers={'Authorization': 'Bearer invalid-token'})
    missing_response = client.get('/auth/me')

    assert invalid_response.status_code == 401
    assert invalid_response.json()['detail'] == 'Invalid authorization token'
    assert missing_response.status_code == 401


def test_profile_me_get_and_put_contract(app_config, monkeypatch, token_auth_stub) -> None:
    """Profile endpoints should return and update profile for authenticated user."""
    profile_state = {
        'user_id': 'user-123',
        'goals': ['Improve composition'],
        'preferred_styles': ['watercolor'],
        'disliked_styles': [],
        'favorite_artists': ['John Singer Sargent'],
        'experience_level': 'beginner',
        'retain_memory': True,
    }

    class _FakeProfileService:
        def __init__(self, config, logger) -> None:
            self._config = config
            self._logger = logger

        def get_profile(self, user_id: str):
            if profile_state['user_id'] != user_id:
                return None
            return profile_state.copy()

        def upsert_profile(self, profile):
            profile_state.update(profile.model_dump())
            return profile_state.copy()

    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.profile.ProfileService',
        _FakeProfileService,
    )

    app = FastAPI()
    app.include_router(create_profile_router(app_config))
    client = TestClient(app)
    headers = {'Authorization': 'Bearer valid-token'}

    get_response = client.get('/profile/me', headers=headers)
    put_response = client.put(
        '/profile/me',
        headers=headers,
        json={
            'goals': ['Build consistent anatomy'],
            'preferred_styles': ['charcoal'],
            'disliked_styles': ['pixel art'],
            'favorite_artists': ['Kim Jung Gi'],
            'experience_level': 'intermediate',
            'retain_memory': False,
        },
    )

    assert get_response.status_code == 200
    assert get_response.json()['user_id'] == 'user-123'
    assert put_response.status_code == 200
    assert put_response.json()['experience_level'] == 'intermediate'
    assert put_response.json()['retain_memory'] is False


def test_profile_me_put_rejects_invalid_payload_type(
    app_config,
    monkeypatch,
    token_auth_stub,
) -> None:
    """`/profile/me` should validate payload shape."""

    class _FakeProfileService:
        def __init__(self, config, logger) -> None:
            self._config = config
            self._logger = logger

        def get_profile(self, _user_id: str):
            return None

        def upsert_profile(self, profile):
            return profile

    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.profile.ProfileService',
        _FakeProfileService,
    )

    app = FastAPI()
    app.include_router(create_profile_router(app_config))
    client = TestClient(app)

    response = client.put(
        '/profile/me',
        headers={'Authorization': 'Bearer valid-token'},
        json={'goals': 'not-a-list'},
    )

    assert response.status_code == 422


def test_portfolio_history_me_returns_items(app_config, monkeypatch, token_auth_stub) -> None:
    """History endpoint returns normalized portfolio/critique item payloads."""

    class _FakeVectorService:
        def search_user_history(self, **_kwargs):
            return [
                {
                    'id': 'item-1',
                    'type': 'portfolio_item',
                    'user_id': 'user-123',
                    'filename': 'sketch.png',
                    'tags': ['gesture'],
                    'description': 'Warmup sketch',
                }
            ]

        def get_point_by_id(self, *_args, **_kwargs):
            return None

    class _FakeStorageService:
        def __init__(self, _config) -> None:
            pass

        def create_signed_url(self, path: str) -> str:
            return f'https://cdn.example/{path}'

    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.portfolio.get_vector_service',
        lambda _config: _FakeVectorService(),
    )
    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.portfolio.StorageService',
        _FakeStorageService,
    )

    app = FastAPI()
    limiter = create_test_limiter()
    install_slowapi(app, limiter)
    app.include_router(create_portfolio_router(app_config, limiter))
    client = TestClient(app)

    response = client.get('/portfolio/history/me', headers={'Authorization': 'Bearer valid-token'})

    assert response.status_code == 200
    assert response.json()[0]['id'] == 'item-1'
    assert response.json()[0]['type'] == 'portfolio_item'


def test_portfolio_history_me_skips_rows_that_fail_response_validation(
    app_config, monkeypatch, token_auth_stub
) -> None:
    """One invalid Qdrant payload must not return 500 for the whole history list."""

    class _FakeVectorService:
        def search_user_history(self, **_kwargs):
            return [
                {
                    'id': 'bad-critique',
                    'type': 'critique',
                    'user_id': 'user-123',
                    'filename': 'bad.jpg',
                    'score': 99,
                    'timestamp': '2020-01-01T00:00:00Z',
                },
                {
                    'id': 'good-item',
                    'type': 'portfolio_item',
                    'user_id': 'user-123',
                    'filename': 'ok.png',
                    'tags': [],
                },
            ]

        def get_point_by_id(self, *_args, **_kwargs):
            return None

    class _FakeStorageService:
        def __init__(self, _config) -> None:
            pass

        def create_signed_url(self, path: str) -> str:
            return f'https://cdn.example/{path}'

    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.portfolio.get_vector_service',
        lambda _config: _FakeVectorService(),
    )
    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.portfolio.StorageService',
        _FakeStorageService,
    )

    app = FastAPI()
    limiter = create_test_limiter()
    install_slowapi(app, limiter)
    app.include_router(create_portfolio_router(app_config, limiter))
    client = TestClient(app)

    response = client.get('/portfolio/history/me', headers={'Authorization': 'Bearer valid-token'})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]['id'] == 'good-item'


def test_portfolio_history_me_rejects_invalid_limit(app_config, monkeypatch, token_auth_stub) -> None:
    """Query params should enforce configured validation constraints."""

    class _FakeVectorService:
        def search_user_history(self, **_kwargs):
            return []

        def get_point_by_id(self, *_args, **_kwargs):
            return None

    class _FakeStorageService:
        def __init__(self, _config) -> None:
            pass

        def create_signed_url(self, path: str) -> str:
            return path

    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.portfolio.get_vector_service',
        lambda _config: _FakeVectorService(),
    )
    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.portfolio.StorageService',
        _FakeStorageService,
    )

    app = FastAPI()
    limiter = create_test_limiter()
    install_slowapi(app, limiter)
    app.include_router(create_portfolio_router(app_config, limiter))
    client = TestClient(app)

    response = client.get(
        '/portfolio/history/me?limit=0',
        headers={'Authorization': 'Bearer valid-token'},
    )

    assert response.status_code == 422


def test_progress_me_returns_progress_payload(app_config, monkeypatch, token_auth_stub) -> None:
    """Progress endpoint should map repository rows into response contract."""

    class _FakeUserProgressRepo:
        def __init__(self, _sb, _logger) -> None:
            pass

        def get(self, _user_id: str):
            return None

        def default(self, user_id: str):
            return SimpleNamespace(
                user_id=user_id,
                total_xp=150,
                current_level=3,
                streak_count=4,
                streak_last_date=None,
                badges=['first-critique'],
            )

    class _FakeProgressSnapshotRepo:
        def __init__(self, _sb, _logger) -> None:
            pass

        def list_active_for_user(self, _user_id: str, limit: int = 10):
            del limit
            return [
                SimpleNamespace(
                    id='snap-1',
                    critique_id='crit-1',
                    rubric_key='fundamentals.v1',
                    aggregate_score=7.5,
                    created_at=None,
                )
            ]

    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.progress.create_sync_supabase_service_client',
        lambda _config: object(),
    )
    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.progress.UserProgressRepository',
        _FakeUserProgressRepo,
    )
    monkeypatch.setattr(
        'ule.artmentorai_project.endpoints.progress.ProgressSnapshotRepository',
        _FakeProgressSnapshotRepo,
    )

    app = FastAPI()
    app.include_router(create_progress_router(app_config))
    client = TestClient(app)

    response = client.get('/progress/me', headers={'Authorization': 'Bearer valid-token'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user_id'] == 'user-123'
    assert payload['total_xp'] == 150
    assert payload['latest_snapshot']['id'] == 'snap-1'


def test_progress_me_requires_authentication(app_config) -> None:
    """Progress endpoint should reject requests without bearer credentials."""
    app = FastAPI()
    app.include_router(create_progress_router(app_config))
    client = TestClient(app)

    response = client.get('/progress/me')

    assert response.status_code == 401
