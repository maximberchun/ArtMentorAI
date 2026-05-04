"""Production validation for CORS-related settings."""

import logging

import pytest

from ule.artmentorai_project.config import AppConfig


def test_production_requires_https_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('GEMINI__API_KEY', 'k')
    monkeypatch.setenv('SUPABASE__URL', 'https://x.supabase.co')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv(
        'ALLOWED_ORIGINS',
        '["https://app.example.com","http://legacy.example.com"]',
    )
    with pytest.raises(ValueError, match='HTTPS'):
        AppConfig()


def test_production_rejects_wildcard_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('GEMINI__API_KEY', 'k')
    monkeypatch.setenv('SUPABASE__URL', 'https://x.supabase.co')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('ALLOWED_ORIGINS', '["*"]')
    with pytest.raises(ValueError, match='Wildcard'):
        AppConfig()


def test_development_allows_http_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('GEMINI__API_KEY', 'k')
    monkeypatch.setenv('SUPABASE__URL', 'https://x.supabase.co')
    monkeypatch.setenv('ENVIRONMENT', 'development')
    cfg = AppConfig()
    cfg.set_logger(logging.getLogger('tests'))
    assert 'http://localhost:5173' in cfg.allowed_origins
