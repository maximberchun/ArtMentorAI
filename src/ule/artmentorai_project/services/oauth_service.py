"""OAuth service for handling Supabase OAuth flows (Google, etc.)."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from ..config import AppConfig


@dataclass
class OAuthTokenResponse:
    """Response from Supabase OAuth token exchange."""

    access_token: str
    refresh_token: str | None
    expires_in: int
    token_type: str
    user_id: str


def generate_pkce_pair() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` for Supabase S256 PKCE."""
    code_verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    return code_verifier, code_challenge


class OAuthService:
    """Handle OAuth token exchange with Supabase Auth."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._auth_url = config.supabase.resolved_auth_url()

    async def exchange_pkce_auth_code(
        self,
        auth_code: str,
        code_verifier: str,
    ) -> OAuthTokenResponse:
        """Exchange a Supabase OAuth auth code using PKCE (GoTrue ``grant_type=pkce``)."""
        anon = self._config.supabase.anon_key
        if not anon:
            msg = 'Supabase anon key is required for OAuth token exchange'
            raise RuntimeError(msg)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self._auth_url}/token?grant_type=pkce',
                headers={
                    'apikey': anon,
                    'Authorization': f'Bearer {anon}',
                    'Content-Type': 'application/json',
                },
                json={
                    'auth_code': auth_code,
                    'code_verifier': code_verifier,
                },
            )
            response.raise_for_status()
            data = response.json()

        access_token, refresh_token, expires_in, token_type, user_id = _parse_token_payload(data)
        return OAuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            token_type=token_type,
            user_id=user_id,
        )

    async def link_identity(
        self, access_token: str, linked_provider: str, linked_token: str
    ) -> dict:
        """Link an OAuth identity to an existing user.

        Used when a user who signed up with email/password wants to add Google OAuth.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self._auth_url}/user/identities',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'apikey': self._config.supabase.anon_key,
                },
                json={
                    'provider': linked_provider,
                    'id_token': linked_token,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_user_identities(self, access_token: str) -> list[dict]:
        """Get all linked identities for a user."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f'{self._auth_url}/user/identities',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'apikey': self._config.supabase.anon_key,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get('identities', [])


def _parse_token_payload(data: dict) -> tuple[str, str | None, int, str, str]:
    """Normalize GoTrue token JSON (flat or nested ``session``) into token fields."""
    session = data.get('session')
    if isinstance(session, dict):
        access_token = session.get('access_token', '')
        refresh_token = session.get('refresh_token')
        expires_in = int(session.get('expires_in', data.get('expires_in', 3600)))
        token_type = str(session.get('token_type', data.get('token_type', 'bearer')))
    else:
        access_token = data.get('access_token', '')
        refresh_token = data.get('refresh_token')
        expires_in = int(data.get('expires_in', 3600))
        token_type = str(data.get('token_type', 'bearer'))

    user = data.get('user')
    user_id = ''
    if isinstance(user, dict):
        user_id = str(user.get('id', ''))

    if not access_token:
        msg = 'Token response missing access_token'
        raise ValueError(msg)

    return access_token, refresh_token, expires_in, token_type, user_id
