"""Integration tests for server-mediated Google OAuth helpers."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ule.artmentorai_project.config import AppConfig
from ule.artmentorai_project.endpoints.auth import create_auth_router
from ule.artmentorai_project.services.oauth_service import OAuthService, OAuthTokenResponse

_OAUTH_TOKEN_TYPE = 'bearer'


def test_google_oauth_url_includes_pkce_and_state(app_config: AppConfig) -> None:
    app = FastAPI()
    app.include_router(create_auth_router(app_config))
    with TestClient(app) as client:
        response = client.post('/auth/google/url')
    assert response.status_code == 200
    body = response.json()
    state = body.get('state')
    assert state is not None
    assert state != ''
    url = body['url']
    assert 'code_challenge=' in url
    assert 'code_challenge_method=S256' in url
    assert state in url


def test_google_callback_rejects_unknown_state(app_config: AppConfig) -> None:
    app = FastAPI()
    app.include_router(create_auth_router(app_config))
    with TestClient(app) as client:
        response = client.post(
            '/auth/google/callback',
            json={'code': 'any', 'state': 'not-issued'},
        )
    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid or expired OAuth state'


def test_google_callback_exchanges_when_state_valid(
    app_config: AppConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    app.include_router(create_auth_router(app_config))
    with TestClient(app) as client:
        url_body = client.post('/auth/google/url').json()
        state = url_body['state']

        async def _fake_exchange(
            _self: OAuthService,
            _code: str,
            _verifier: str,
        ) -> OAuthTokenResponse:
            test_access = 'unit-test-access-jwt'
            test_refresh = 'unit-test-refresh-token'
            return OAuthTokenResponse(
                access_token=test_access,
                refresh_token=test_refresh,
                expires_in=3600,
                token_type=_OAUTH_TOKEN_TYPE,
                user_id='user-99',
            )

        monkeypatch.setattr(OAuthService, 'exchange_pkce_auth_code', _fake_exchange)
        response = client.post(
            '/auth/google/callback',
            json={'code': 'dummy-code', 'state': state},
        )
    assert response.status_code == 200
    data = response.json()
    assert data['access_token'] == 'unit-test-access-jwt'
    assert data['user_id'] == 'user-99'


def test_google_callback_second_submit_fails(app_config: AppConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    app = FastAPI()
    app.include_router(create_auth_router(app_config))

    async def _fake_exchange(
        _self: OAuthService,
        _code: str,
        _verifier: str,
    ) -> OAuthTokenResponse:
        test_access = 'unit-test-access-jwt-2'
        return OAuthTokenResponse(
            access_token=test_access,
            refresh_token=None,
            expires_in=1,
            token_type=_OAUTH_TOKEN_TYPE,
            user_id='u',
        )

    monkeypatch.setattr(OAuthService, 'exchange_pkce_auth_code', _fake_exchange)
    with TestClient(app) as client:
        state = client.post('/auth/google/url').json()['state']
        first = client.post('/auth/google/callback', json={'code': 'c', 'state': state})
        second = client.post('/auth/google/callback', json={'code': 'c', 'state': state})
    assert first.status_code == 200
    assert second.status_code == 400
