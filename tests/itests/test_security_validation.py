"""Security regression tests: rate limits, response headers, and CORS policy."""

from __future__ import annotations

import logging
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from PIL import Image
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from tests.conftest import create_test_limiter, install_slowapi
from tests.itests.test_analysis_endpoint import (
    _FakeAgentService,
    _FakeProfileService,
    _FailingVectorService,
)
from ule.artmentorai_project.config import AppConfig
from ule.artmentorai_project.endpoints.analysis import create_analysis_router
from ule.artmentorai_project.endpoints.portfolio import create_portfolio_router
from ule.artmentorai_project.models import AuthUser


def _security_app_config(monkeypatch: pytest.MonkeyPatch, **rate_env: str) -> AppConfig:
    monkeypatch.setenv('OPENROUTER__API_KEY', 'test-openrouter-api-key')
    monkeypatch.setenv('SUPABASE__URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE__ANON_KEY', 'test-anon-key')
    for key, value in rate_env.items():
        monkeypatch.setenv(key, value)
    cfg = AppConfig()
    cfg.set_logger(logging.getLogger('tests.security_validation'))
    return cfg


def _attach_rate_limit_handler(app: FastAPI) -> None:
    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
        # slowapi's handler returns a concrete Response (not a coroutine).
        return _rate_limit_exceeded_handler(request, exc)


def _build_rate_limited_analysis_client(
    app_config: AppConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    import ule.artmentorai_project.endpoints.analysis as analysis_module

    async def _verify_access_token(_self, token: str) -> AuthUser:
        if token == 'invalid-token':
            raise HTTPException(status_code=401, detail='Invalid authorization token')
        return AuthUser(user_id='user-rl', email='rl@example.com', role='authenticated')

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
    limiter = create_test_limiter()
    install_slowapi(app, limiter)
    _attach_rate_limit_handler(app)
    app.include_router(create_analysis_router(app_config, limiter))
    return TestClient(app)


def _tiny_png_bytes() -> bytes:
    buf = BytesIO()
    Image.new('RGB', (2, 2), color=(1, 2, 3)).save(buf, format='PNG')
    return buf.getvalue()


def _build_rate_limited_portfolio_client(
    app_config: AppConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    import ule.artmentorai_project.endpoints.portfolio as portfolio_module

    async def _verify_access_token(_self, token: str) -> AuthUser:
        return AuthUser(user_id='user-pf', email='pf@example.com', role='authenticated')

    monkeypatch.setattr(
        'ule.artmentorai_project.services.auth_service.AuthService.verify_access_token',
        _verify_access_token,
    )

    class _FakeVectorService:
        def search_user_history(self, **_kwargs):
            return []

        def get_point_by_id(self, *_args, **_kwargs):
            return None

    class _FakeStorageService:
        def __init__(self, _config) -> None:
            pass

        def upload_image(self, **_kwargs) -> str:
            return 'users/user-pf/portfolio/x.png'

        def delete_file(self, *_args, **_kwargs) -> None:
            return None

        def create_signed_url(self, path: str) -> str:
            return f'https://cdn.example/{path}'

    class _FakeImageRepo:
        def __init__(self, _sb, _logger) -> None:
            self._n = 0

        def create(self, **_kwargs):
            self._n += 1
            return SimpleNamespace(id=f'img-{self._n}')

        def soft_delete(self, *_a, **_k) -> None:
            return None

    class _FakePortfolioRepo:
        def __init__(self, _sb, _logger) -> None:
            self._n = 0

        def create(self, **kwargs):
            self._n += 1
            return SimpleNamespace(
                id=f'row-{self._n}',
                user_id=kwargs['user_id'],
                image_asset_id=kwargs['image_asset_id'],
            )

        def soft_delete(self, *_a, **_k) -> None:
            return None

    class _FakeSyncRepo:
        def __init__(self, _sb, _logger) -> None:
            pass

        def enqueue(self, *_a, **_k) -> None:
            return None

    monkeypatch.setattr(portfolio_module, 'get_vector_service', lambda _config: _FakeVectorService())
    monkeypatch.setattr(portfolio_module, 'StorageService', _FakeStorageService)
    monkeypatch.setattr(
        portfolio_module,
        'create_sync_supabase_service_client',
        lambda _config: object(),
    )
    monkeypatch.setattr(portfolio_module, 'ImageAssetRepository', _FakeImageRepo)
    monkeypatch.setattr(portfolio_module, 'PortfolioItemRepository', _FakePortfolioRepo)
    monkeypatch.setattr(portfolio_module, 'VectorSyncJobRepository', _FakeSyncRepo)

    app = FastAPI()
    limiter = create_test_limiter()
    install_slowapi(app, limiter)
    _attach_rate_limit_handler(app)
    app.include_router(create_portfolio_router(app_config, limiter))
    return TestClient(app)


def test_critique_endpoint_enforces_rate_limit_after_burst(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expensive critique route should return 429 once the configured per-minute cap is exceeded."""
    cfg = _security_app_config(monkeypatch, RATE_LIMITS__CRITIQUE='1/minute')
    client = _build_rate_limited_analysis_client(cfg, monkeypatch)
    headers = {'Authorization': 'Bearer valid-token'}
    data = {'user_input': 'Critique my gesture drawing.'}

    first = client.post('/analysis/critique', data=data, headers=headers)
    second = client.post('/analysis/critique', data=data, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert 'Rate limit exceeded' in second.json().get('error', '')


def test_chat_endpoint_enforces_rate_limit_after_burst(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chat route should be independently throttled from critique."""
    cfg = _security_app_config(monkeypatch, RATE_LIMITS__CHAT='1/minute')
    client = _build_rate_limited_analysis_client(cfg, monkeypatch)
    headers = {'Authorization': 'Bearer valid-token'}
    body = {'message': 'What is negative space?'}

    first = client.post('/analysis/chat', json=body, headers=headers)
    second = client.post('/analysis/chat', json=body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert 'Rate limit exceeded' in second.json().get('error', '')


def test_portfolio_upload_enforces_rate_limit_after_burst(monkeypatch: pytest.MonkeyPatch) -> None:
    """Portfolio upload must not allow unbounded parallel abuse of storage."""
    cfg = _security_app_config(monkeypatch, RATE_LIMITS__PORTFOLIO_UPLOAD='1/minute')
    client = _build_rate_limited_portfolio_client(cfg, monkeypatch)
    headers = {'Authorization': 'Bearer valid-token'}
    png = _tiny_png_bytes()
    files = [('files', ('burst.png', BytesIO(png), 'image/png'))]

    first = client.post('/portfolio/upload', headers=headers, files=files)
    second = client.post('/portfolio/upload', headers=headers, files=files)

    assert first.status_code == 200
    assert second.status_code == 429
    assert 'Rate limit exceeded' in second.json().get('error', '')


def test_global_health_responses_include_security_headers(test_client: TestClient) -> None:
    """Baseline API responses should carry conservative browser-safety headers."""
    response = test_client.get('/health')
    assert response.status_code == 200
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-Frame-Options') == 'DENY'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    csp = response.headers.get('Content-Security-Policy', '')
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


def test_cors_allows_configured_dev_origin_on_preflight(test_client: TestClient) -> None:
    """Browser preflight from an allowed dev origin should succeed with explicit method allowlist."""
    response = test_client.options(
        '/health',
        headers={
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'GET',
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get('access-control-allow-origin') == 'http://localhost:5173'


def test_cors_does_not_reflect_disallowed_origin(test_client: TestClient) -> None:
    """Untrusted Origin values must not receive a blanket allow header."""
    response = test_client.get(
        '/health',
        headers={'Origin': 'https://attacker.example'},
    )
    assert response.status_code == 200
    assert response.headers.get('access-control-allow-origin') != 'https://attacker.example'
