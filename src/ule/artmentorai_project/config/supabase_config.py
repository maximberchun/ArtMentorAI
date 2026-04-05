"""Supabase configuration (Auth/JWT verification).

We verify Supabase access tokens by validating the JWT signature against the
project JWKS endpoint.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class SupabaseConfig(BaseSettings):
    """Configuration for Supabase integration."""

    url: str = Field(..., description='Supabase project URL')

    anon_key: str = Field(
        default='',
        description='Supabase anon/public key safe to expose to client',
    )

    service_role_key: str = Field(
        default='',
        description='Supabase service role key SERVER ONLY NEVER EXPOSED',
    )

    google_oauth_client_id: str = Field(
        default='',
        description='Google OAuth client ID for Supabase used in OAuth callback',
    )

    google_oauth_client_secret: str = Field(
        default='',
        description='Google OAuth client secret for Supabase used in OAuth callback',
    )

    storage_bucket: str = Field(
        default='artworks',
        description='Supabase Storage bucket used for uploaded artwork files',
    )

    signed_url_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=604800,
        description='Signed URL expiration in seconds',
    )

    # If omitted derived from 'url' as: {url}/auth/v1/.well-known/jwks.json
    jwks_url: str | None = Field(
        default=None,
        description='JWKS URL used to verify Supabase JWTs (optional)',
    )

    jwt_aud: str = Field(
        default='authenticated',
        description='Expected JWT audience for Supabase access tokens',
    )

    # If omitted derived as '{url}/auth/v1'
    jwt_iss: str | None = Field(
        default=None,
        description='Expected JWT issuer (optional)',
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

    def resolved_auth_url(self) -> str:
        """Return the Supabase Auth URL for OAuth operations."""
        return f'{self.url.rstrip("/")}/auth/v1'
