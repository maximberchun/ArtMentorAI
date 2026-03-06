"""Endpoints for managing user profiles (goals and preferences)."""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, status

from ..config import AppConfig
from ..models import UserProfile, UserProfileBase
from ..services import ProfileService


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

    profile_service = ProfileService(logger=config.logger)

    @router.get(
        '/{user_id}',
        response_model=UserProfile,
        summary='Get user profile',
        description='Retrieve the stored profile (goals and preferences) for a user.',
    )
    async def get_profile(user_id: str) -> UserProfile:
        try:
            profile = profile_service.get_profile(user_id)
        except RuntimeError as e:
            config.logger.exception('Failed to load profile for user_id=%s', user_id)
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
        '/{user_id}',
        response_model=UserProfile,
        summary='Create or update user profile',
        description=(
            'Create or update the profile for the given user, including goals, '
            'preferred and disliked styles, favorite artists, and experience level.'
        ),
    )
    async def upsert_profile(
        user_id: str,
        payload: Annotated[
            UserProfileBase,
            Body(
                description=(
                    'Profile fields to set for the user. The `user_id` is taken '
                    'from the URL path and does not need to be included here.'
                ),
            ),
        ],
    ) -> UserProfile:
        profile = UserProfile(user_id=user_id, **payload.model_dump())
        try:
            saved = profile_service.upsert_profile(profile)
        except RuntimeError as e:
            config.logger.exception('Failed to save profile for user_id=%s', user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error saving profile: {e!s}',
            ) from e
        return saved

    return router


__all__ = [
    'create_profile_router',
]

