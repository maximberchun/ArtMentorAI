"""Authenticated user identity derived from Supabase JWT."""

from pydantic import BaseModel, Field


class AuthUser(BaseModel):
    """Minimal identity extracted from a verified Supabase access token."""

    user_id: str = Field(..., description='Supabase user id (JWT subject)')
    email: str | None = Field(default=None, description='User email if present in token claims')
    role: str | None = Field(default=None, description='Supabase role')
