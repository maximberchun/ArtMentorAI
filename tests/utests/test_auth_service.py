"""Unit tests for Supabase token verification service."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from jwt import ExpiredSignatureError
from jwt import PyJWTError

from ule.artmentorai_project.services.auth_service import AuthService


def test_verify_access_token_rejects_invalid_jwt_header(app_config, monkeypatch) -> None:
    """Invalid JWT header data should return a 401."""
    service = AuthService(app_config)

    def _raise_bad_header(_token: str) -> dict[str, str]:
        raise PyJWTError('invalid header')

    monkeypatch.setattr(
        'ule.artmentorai_project.services.auth_service.jwt.get_unverified_header',
        _raise_bad_header,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.verify_access_token('bad-token'))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Invalid authorization token'


def test_verify_access_token_rejects_unsupported_algorithm(app_config, monkeypatch) -> None:
    """Tokens signed with unsupported algorithms should be denied."""
    service = AuthService(app_config)
    monkeypatch.setattr(
        'ule.artmentorai_project.services.auth_service.jwt.get_unverified_header',
        lambda _token: {'kid': 'kid-1', 'alg': 'HS256'},
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.verify_access_token('token'))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Unsupported token algorithm'


def test_verify_access_token_returns_auth_user_when_claims_valid(app_config, monkeypatch) -> None:
    """Valid claims should be transformed into an AuthUser model."""
    service = AuthService(app_config)

    async def _fake_get_jwk(_kid: str) -> dict[str, str]:
        return {'kty': 'RSA', 'kid': 'kid-1'}

    monkeypatch.setattr(service, '_get_jwk_for_kid', _fake_get_jwk)
    monkeypatch.setattr(
        'ule.artmentorai_project.services.auth_service.jwt.get_unverified_header',
        lambda _token: {'kid': 'kid-1', 'alg': 'RS256'},
    )
    monkeypatch.setattr(
        'ule.artmentorai_project.services.auth_service.RSAAlgorithm.from_jwk',
        lambda _jwk: 'public-key',
    )
    monkeypatch.setattr(
        'ule.artmentorai_project.services.auth_service.jwt.decode',
        lambda *_args, **_kwargs: {
            'sub': 'user-123',
            'email': 'user@example.com',
            'role': 'authenticated',
        },
    )

    result = asyncio.run(service.verify_access_token('valid-token'))

    assert result.user_id == 'user-123'
    assert result.email == 'user@example.com'
    assert result.role == 'authenticated'


def test_verify_access_token_maps_expired_signature_to_401(app_config, monkeypatch) -> None:
    """Expired signatures should be returned as explicit 401 token-expired errors."""
    service = AuthService(app_config)

    async def _fake_get_jwk(_kid: str) -> dict[str, str]:
        return {'kty': 'RSA', 'kid': 'kid-1'}

    monkeypatch.setattr(service, '_get_jwk_for_kid', _fake_get_jwk)
    monkeypatch.setattr(
        'ule.artmentorai_project.services.auth_service.jwt.get_unverified_header',
        lambda _token: {'kid': 'kid-1', 'alg': 'RS256'},
    )
    monkeypatch.setattr(
        'ule.artmentorai_project.services.auth_service.RSAAlgorithm.from_jwk',
        lambda _jwk: 'public-key',
    )

    def _raise_expired(*_args, **_kwargs):
        raise ExpiredSignatureError('expired')

    monkeypatch.setattr('ule.artmentorai_project.services.auth_service.jwt.decode', _raise_expired)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.verify_access_token('expired-token'))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Token expired'
