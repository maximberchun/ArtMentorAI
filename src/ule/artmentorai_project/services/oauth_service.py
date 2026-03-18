"""OAuth service for handling Supabase OAuth flows (Google, etc.)."""

from __future__ import annotations

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


class OAuthService:
    """Handle OAuth token exchange with Supabase Auth."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._auth_url = config.supabase.resolved_auth_url()

    async def exchange_code_for_tokens(self, code: str) -> OAuthTokenResponse:
        """Exchange an OAuth authorization code for access tokens.

        This is called when Supabase redirects back after Google OAuth.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self._auth_url}/token',
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'client_id': self._config.supabase.google_oauth_client_id,
                    'client_secret': self._config.supabase.google_oauth_client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()

        return OAuthTokenResponse(
            access_token=data['access_token'],
            refresh_token=data.get('refresh_token'),
            expires_in=data.get('expires_in', 3600),
            token_type=data.get('token_type', 'bearer'),
            user_id=data.get('user', {}).get('id', ''),
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
