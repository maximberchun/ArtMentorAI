"""Authentication/identity endpoints.

The frontend authenticates with Supabase (email/password or Google OAuth) and
sends the Supabase access token to this API. We verify the token and derive
`user_id` from it.

For Google OAuth client-side flow using Supabase JS SDK:
1. Frontend calls supabase.auth.signInWithOAuth({ provider: 'google' })
2. Supabase redirects to Google
3. Google redirects back to frontend with auth code
4. Supabase JS SDK exchanges code for tokens automatically
5. Frontend sends access_token to this API for authenticated requests

Server-side OAuth (optional): use ``POST /auth/google/url`` to obtain an
authorize URL with PKCE and ``state``, then ``POST /auth/google/callback`` with
the ``code`` and ``state`` from the redirect. The server binds ``state`` to the
PKCE verifier issued for that flow.

Account linking is automatic in Supabase Auth:
- Same email = same user_id regardless of login method
- Google OAuth and email/password both map to the same Supabase user
"""

import secrets
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..config import AppConfig
from ..models import AuthUser
from ..services.oauth_pkce_store import OAuthPkceStore
from ..services.oauth_service import OAuthService, generate_pkce_pair
from .deps import build_current_user_dependency


class GoogleOAuthUrlResponse(BaseModel):
    """Authorize URL and CSRF ``state`` for the server-mediated OAuth flow."""

    url: str
    state: str
    expires_in: int = Field(
        default=600,
        description='Suggested max seconds before completing the flow',
    )


class GoogleOAuthCallbackRequest(BaseModel):
    """Payload from the OAuth redirect handler (auth code + CSRF state)."""

    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


def create_auth_router(config: AppConfig) -> APIRouter:
    """Create auth router."""
    router = APIRouter(prefix='/auth', tags=['Auth'])
    current_user = build_current_user_dependency(config)
    oauth = OAuthService(config)
    pkce_store = OAuthPkceStore()

    @router.get('/me', summary='Get current user identity')
    async def me(user: Annotated[AuthUser, Depends(current_user)]) -> AuthUser:
        return user

    @router.post(
        '/google/url',
        summary='Get Google OAuth URL for server-side flow (PKCE + state)',
    )
    async def get_google_oauth_url() -> GoogleOAuthUrlResponse:
        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = generate_pkce_pair()
        pkce_store.remember(state, code_verifier)

        params = {
            'provider': 'google',
            'redirect_to': config.supabase.oauth_redirect_url,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'state': state,
        }
        base = f'{config.supabase.url.rstrip("/")}/auth/v1/authorize'
        url = f'{base}?{urlencode(params)}'
        return GoogleOAuthUrlResponse(url=url, state=state, expires_in=600)

    @router.post(
        '/google/callback',
        summary='Exchange OAuth code for tokens (server-side OAuth, PKCE)',
    )
    async def google_callback(body: GoogleOAuthCallbackRequest) -> dict:
        code_verifier = pkce_store.pop_verifier(body.state)
        if code_verifier is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid or expired OAuth state',
            )
        try:
            tokens = await oauth.exchange_pkce_auth_code(body.code, code_verifier)
        except (httpx.HTTPError, ValueError, RuntimeError):
            config.logger.exception('Supabase OAuth token exchange failed')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='OAuth code exchange failed',
            ) from None
        return {
            'access_token': tokens.access_token,
            'refresh_token': tokens.refresh_token,
            'expires_in': tokens.expires_in,
            'token_type': tokens.token_type,
            'user_id': tokens.user_id,
        }

    @router.get('/providers')
    async def get_providers() -> dict:
        return {
            'providers': [
                {
                    'id': 'google',
                    'name': 'Google',
                    'note': (
                        'Prefer client-side signInWithOAuth with the Supabase JS SDK, or '
                        'POST /auth/google/url for a PKCE-bound server-mediated URL'
                    ),
                }
            ]
        }

    return router
