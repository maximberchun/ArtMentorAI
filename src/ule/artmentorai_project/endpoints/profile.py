"""Endpoints for managing user profiles (goals and preferences)."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from ..config import AppConfig
from ..models import AuthUser, UserProfile, UserProfileBase
from ..services import ProfileService
from .deps import build_current_user_dependency


def create_profile_router(config: AppConfig) -> APIRouter:
    """
    Create router for user profile CRUD operations.

    The profile API allows the frontend to persist and retrieve a user's
    long-term goals, stylistic preferences, and favorite artists so that
    critiques can be personalised.
    """
    router = APIRouter(
        prefix='/profile',
        tags=['Profile'],
        responses={
            404: {'description': 'Profile not found'},
            500: {'description': 'Server error while accessing profile storage'},
        },
    )

    profile_service = ProfileService(config=config, logger=config.logger)
    current_user = build_current_user_dependency(config)

    @router.get(
        '/me',
        summary='Get user profile',
        description='Retrieve the stored profile (goals and preferences) for the current user.',
    )
    async def get_profile(user: Annotated[AuthUser, Depends(current_user)]) -> UserProfile:
        try:
            profile = profile_service.get_profile(user.user_id)
        except RuntimeError as e:
            config.logger.exception('Failed to load profile for user_id=%s', user.user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error loading profile: {e!s}',
            ) from e

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Profile not found',
            )
        return profile

    @router.put(
        '/me',
        summary='Create or update user profile',
        description=(
            'Create or update the profile for the current user, including goals, '
            'preferred and disliked styles, favorite artists, and experience level.'
        ),
    )
    async def upsert_profile(
        payload: Annotated[
            UserProfileBase,
            Body(
                description=(
                    'Profile fields to set for the user. The `user_id` is taken '
                    'from the verified access token and does not need to be included here.'
                ),
            ),
        ],
        user: Annotated[AuthUser, Depends(current_user)],
    ) -> UserProfile:
        profile = UserProfile(user_id=user.user_id, **payload.model_dump())
        try:
            saved = profile_service.upsert_profile(profile)
        except RuntimeError as e:
            config.logger.exception('Failed to save profile for user_id=%s', user.user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error saving profile: {e!s}',
            ) from e
        return saved

    # Backward-compatible endpoints (do not trust caller-provided user_id).
    @router.get(
        '/{user_id}',
        summary='Get user profile (deprecated)',
        description='Deprecated. Use GET /profile/me. Only allowed for the current user.',
        deprecated=True,
    )
    async def get_profile_deprecated(
        user_id: str,
        user: Annotated[AuthUser, Depends(current_user)],
    ) -> UserProfile:
        if user_id != user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden')
        return await get_profile(user=user)

    @router.put(
        '/{user_id}',
        summary='Create/update user profile (deprecated)',
        description='Deprecated. Use PUT /profile/me. Only allowed for the current user.',
        deprecated=True,
    )
    async def upsert_profile_deprecated(
        user_id: str,
        payload: Annotated[UserProfileBase, Body(description='Profile fields to set.')],
        user: Annotated[AuthUser, Depends(current_user)],
    ) -> UserProfile:
        if user_id != user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden')
        return await upsert_profile(user=user, payload=payload)

    return router


__all__ = [
    'create_profile_router',
]

