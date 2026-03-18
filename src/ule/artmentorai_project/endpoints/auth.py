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

Account linking is automatic in Supabase Auth:
- Same email = same user_id regardless of login method
- Google OAuth and email/password both map to the same Supabase user
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import AppConfig
from ..models import AuthUser
from ..services.auth_service import AuthService
from ..services.oauth_service import OAuthService

_bearer = HTTPBearer(auto_error=True)


def _build_current_user_dependency(config: AppConfig) -> Callable[..., Awaitable[AuthUser]]:
    auth = AuthService(config)

    async def _current_user(
        creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    ) -> AuthUser:
        return await auth.verify_access_token(creds.credentials)

    return _current_user


def create_auth_router(config: AppConfig) -> APIRouter:
    """Create auth router."""
    router = APIRouter(prefix='/auth', tags=['Auth'])
    current_user = _build_current_user_dependency(config)
    oauth = OAuthService(config)

    @router.get('/me', summary='Get current user identity')
    async def me(user: Annotated[AuthUser, Depends(current_user)]) -> AuthUser:
        return user

    @router.post(
        '/google/url',
        summary='Get Google OAuth URL for server-side flow',
    )
    async def get_google_oauth_url() -> dict:
        url = f'{config.supabase.url}/auth/v1/authorize?provider=google'
        return {
            'url': url,
            'instructions': 'Redirect user to this URL. After auth Supabase redirects to your redirect_uri with ?code=xxx',  # noqa: E501
        }

    @router.post(
        '/google/callback',
        summary='Exchange OAuth code for tokens (server-side OAuth)',
    )
    async def google_callback(code: str) -> dict:
        tokens = await oauth.exchange_code_for_tokens(code)
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
                    'url': f'{config.supabase.url}/auth/v1/authorize?provider=google',
                }
            ]
        }

    return router
