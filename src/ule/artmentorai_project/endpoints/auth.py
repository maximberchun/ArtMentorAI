"""Authentication/identity endpoints.

The frontend authenticates with Supabase (email/password or Google OAuth) and
sends the Supabase access token to this API. We verify the token and derive
`user_id` from it.
"""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import AppConfig
from ..models import AuthUser
from ..services.auth_service import AuthService

_bearer = HTTPBearer(auto_error=True)


def _build_current_user_dependency(config: AppConfig) -> Callable[..., Awaitable[AuthUser]]:
    auth = AuthService(config)

    async def _current_user(
        creds: HTTPAuthorizationCredentials = Depends(_bearer),
    ) -> AuthUser:
        return await auth.verify_access_token(creds.credentials)

    return _current_user


def create_auth_router(config: AppConfig) -> APIRouter:
    """Create auth router."""
    router = APIRouter(prefix='/auth', tags=['Auth'])
    current_user = _build_current_user_dependency(config)

    @router.get('/me', response_model=AuthUser, summary='Get current user identity')
    async def me(user: AuthUser = Depends(current_user)) -> AuthUser:
        return user

    return router

