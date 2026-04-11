"""Supabase Auth verification helpers.

This service verifies Supabase access tokens (JWTs) using the project's JWKS
(RS256 or ES256, matching current Supabase signing keys).
The API does not perform login itself; the frontend authenticates with Supabase
and forwards the access token via `Authorization: Bearer <token>`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, status
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from ..config import AppConfig  # noqa: TC001
from ..models import AuthUser


@dataclass(frozen=True)
class _CachedJwks:
    keys_by_kid: dict[str, Any]
    fetched_at: float


class AuthService:
    """Verify Supabase JWTs and derive an authenticated user identity."""

    _JWKS_CACHE_TTL_S = 60 * 15  # 15 minutes

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._jwks_cache: _CachedJwks | None = None

    async def _fetch_jwks(self) -> _CachedJwks:
        jwks_url = self._config.supabase.resolved_jwks_url()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            data = resp.json()

        keys_by_kid: dict[str, Any] = {}
        for jwk in data.get('keys', []):
            kid = jwk.get('kid')
            if kid:
                keys_by_kid[str(kid)] = jwk

        if not keys_by_kid:
            msg = f'No JWKS signing keys found at {jwks_url}'
            raise RuntimeError(msg)

        return _CachedJwks(keys_by_kid=keys_by_kid, fetched_at=time.time())

    async def _get_jwk_for_kid(self, kid: str) -> Any:
        now = time.time()
        cache = self._jwks_cache

        cache_valid = cache is not None and (now - cache.fetched_at) < self._JWKS_CACHE_TTL_S
        if not cache_valid:
            self._jwks_cache = await self._fetch_jwks()
            cache = self._jwks_cache

        assert cache is not None  # noqa: S101
        jwk = cache.keys_by_kid.get(kid)
        if jwk is not None:
            return jwk

        # Key rotation: refresh once and try again
        self._jwks_cache = await self._fetch_jwks()
        jwk = self._jwks_cache.keys_by_kid.get(kid)
        if jwk is None:
            msg = f'Unknown signing key id (kid={kid})'
            raise RuntimeError(msg)
        return jwk

    async def verify_access_token(self, token: str) -> AuthUser:
        """Verify a Supabase access token and return the authenticated user."""
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid authorization token',
            ) from e

        kid = header.get('kid')
        alg = header.get('alg')
        if not kid or not alg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid authorization token header',
            )
        if alg not in ('RS256', 'ES256'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Unsupported token algorithm',
            )

        try:
            jwk = await self._get_jwk_for_kid(str(kid))
            if alg == 'RS256':
                public_key = RSAAlgorithm.from_jwk(jwk)
            else:
                public_key = ECAlgorithm.from_jwk(jwk)

            claims = jwt.decode(
                token,
                key=public_key,
                algorithms=[alg],
                audience=self._config.supabase.jwt_aud,
                issuer=self._config.supabase.resolved_issuer(),
                options={
                    'require': ['exp', 'iat', 'sub'],
                },
            )
        except HTTPException:
            raise
        except jwt.ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token expired',
            ) from e
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid authorization token',
            ) from e
        except Exception as e:
            self._config.logger.exception('Failed to verify Supabase token')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token verification failed',
            ) from e

        user_id = str(claims.get('sub') or '')
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token subject',
            )

        email = claims.get('email')
        role = claims.get('role')
        return AuthUser(
            user_id=user_id, email=str(email) if email else None, role=str(role) if role else None
        )
