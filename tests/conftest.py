"""Shared pytest fixtures for backend unit and integration tests."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator  # noqa: TC003
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Ensure local package imports work when project is not installed.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

try:
    from slowapi import Limiter  # noqa: E402
    from slowapi.middleware import SlowAPIMiddleware  # noqa: E402
    from slowapi.util import get_remote_address  # noqa: E402
except ModuleNotFoundError:
    raise

from ule.artmentorai_project.cli import create_app  # noqa: E402
from ule.artmentorai_project.config import AppConfig  # noqa: E402


def create_test_limiter() -> Limiter:
    """Build a SlowAPI limiter for isolated FastAPI apps in tests."""
    return Limiter(key_func=get_remote_address)


def install_slowapi(app: FastAPI, limiter: Limiter) -> None:
    """Attach SlowAPI middleware and ``app.state.limiter`` (required by ``@limiter.limit``)."""
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return default Authorization headers used by authenticated endpoints."""
    return {'Authorization': 'Bearer test-access-token'}


@pytest.fixture
def invalid_auth_headers() -> dict[str, str]:
    """Return malformed Authorization headers for failure-path tests."""
    return {'Authorization': 'Bearer '}


@pytest.fixture
def mock_supabase_client() -> MagicMock:
    """Provide a reusable mocked Supabase service client."""
    return MagicMock(name='supabase_service_client')


@pytest.fixture
def mock_vector_service() -> MagicMock:
    """Provide a reusable mocked vector service."""
    service = MagicMock(name='vector_service')
    service.health_check.return_value = True
    service.search_similar_critiques.return_value = []
    service.search_similar_portfolio_items.return_value = []
    return service


@pytest.fixture
def app_config(monkeypatch: pytest.MonkeyPatch) -> AppConfig:
    """Build AppConfig with test-safe environment variables."""
    monkeypatch.setenv('OPENROUTER__API_KEY', 'test-openrouter-api-key')
    monkeypatch.setenv('SUPABASE__URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE__ANON_KEY', 'test-anon-key')

    config = AppConfig()
    config.set_logger(logging.getLogger('tests'))
    return config


@pytest.fixture
def test_client(
    monkeypatch: pytest.MonkeyPatch,
    app_config: AppConfig,
) -> Iterator[TestClient]:
    """Create a FastAPI test client with external dependencies stubbed."""
    import ule.artmentorai_project.cli as cli_module  # noqa: PLC0415

    def _stub_router(path_prefix: str, tag: str) -> APIRouter:
        router = APIRouter(prefix=path_prefix, tags=[tag])

        @router.get('/health')
        async def _health() -> dict[str, str]:
            return {'status': 'ok', 'router': tag}

        return router

    class _NoopVectorSyncWorker:
        def __init__(self, _config: AppConfig) -> None:
            self._config = _config

        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    monkeypatch.setattr(
        cli_module,
        'create_analysis_router',
        lambda _config, _limiter: _stub_router('/analysis', 'Analysis'),
    )
    monkeypatch.setattr(
        cli_module,
        'create_auth_router',
        lambda _config: _stub_router('/auth', 'Auth'),
    )
    monkeypatch.setattr(
        cli_module,
        'create_profile_router',
        lambda _config: _stub_router('/profile', 'Profile'),
    )
    monkeypatch.setattr(
        cli_module,
        'create_portfolio_router',
        lambda _config, _limiter: _stub_router('/portfolio', 'Portfolio'),
    )
    monkeypatch.setattr(
        cli_module,
        'create_progress_router',
        lambda _config: _stub_router('/progress', 'Progress'),
    )
    monkeypatch.setattr(cli_module, 'VectorSyncWorker', _NoopVectorSyncWorker)

    app = create_app(app_config)
    app.state.test_mocks = SimpleNamespace()

    with TestClient(app) as client:
        yield client
