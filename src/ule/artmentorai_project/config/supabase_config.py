"""Supabase configuration (Auth/JWT verification).

We verify Supabase access tokens by validating the JWT signature against the
project JWKS endpoint.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class SupabaseConfig(BaseSettings):
    """Configuration for Supabase integration."""

    url: str = Field(..., description='Supabase project URL (e.g. https://<ref>.supabase.co)')

    # If omitted derived from 'url' as: {url}/auth/v1/.well-known/jwks.json
    jwks_url: str | None = Field(
        default=None,
        description='JWKS URL used to verify Supabase JWTs (optional override)',
    )

    jwt_aud: str = Field(
        default='authenticated',
        description='Expected JWT audience for Supabase access tokens',
    )

    # If omitted derived as '{url}/auth/v1'
    jwt_iss: str | None = Field(
        default=None,
        description='Expected JWT issuer (optional override)',
    )

    def resolved_jwks_url(self) -> str:
        """Return the JWKS URL to fetch signing keys from."""
        if self.jwks_url:
            return self.jwks_url
        return f'{self.url.rstrip("/")}/auth/v1/.well-known/jwks.json'

    def resolved_issuer(self) -> str:
        """Return expected issuer string for Supabase access tokens."""
        if self.jwt_iss:
            return self.jwt_iss
        return f'{self.url.rstrip("/")}/auth/v1'
