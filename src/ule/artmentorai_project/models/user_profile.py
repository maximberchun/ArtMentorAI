"""User profile models for goals, preferences, and favorite artists."""

from pydantic import BaseModel, Field


class UserProfileBase(BaseModel):
    """Base fields shared by user profile representations."""

    goals: list[str] = Field(
        default_factory=list,
        description='High-level artistic goals the user wants to achieve.',
    )
    preferred_styles: list[str] = Field(
        default_factory=list,
        description='Art styles or genres the user enjoys or wants to emulate.',
    )
    disliked_styles: list[str] = Field(
        default_factory=list,
        description='Art styles or genres the user does not enjoy.',
    )
    favorite_artists: list[str] = Field(
        default_factory=list,
        description='Artists the user finds inspiring or wants to learn from.',
    )
    experience_level: str = Field(
        default='beginner',
        description='Self-reported level: beginner, intermediate, or advanced.',
    )


class UserProfile(UserProfileBase):
    """Complete user profile bound to a concrete user identifier."""

    user_id: str = Field(
        ...,
        description='Unique identifier for the user.',
    )


__all__ = [
    'UserProfileBase',
    'UserProfile',
]

