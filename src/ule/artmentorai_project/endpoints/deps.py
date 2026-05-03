"""Shared FastAPI dependencies for endpoint modules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..services.auth_service import AuthService

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from ..config import AppConfig
    from ..models import AuthUser

_bearer = HTTPBearer(auto_error=True)


def build_current_user_dependency(config: AppConfig) -> Callable[..., Awaitable[AuthUser]]:
    """Return a Depends() callable that resolves the bearer token to ``AuthUser``."""
    auth = AuthService(config)

    async def current_user(
        creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    ) -> AuthUser:
        return await auth.verify_access_token(creds.credentials)

    return current_user
