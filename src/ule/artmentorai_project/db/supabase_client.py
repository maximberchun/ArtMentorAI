"""Supabase client factory for server-side (service role) access."""

from __future__ import annotations

from typing import TYPE_CHECKING

from supabase import acreate_client, create_client

if TYPE_CHECKING:
    from supabase import AsyncClient, Client

    from ..config import AppConfig


async def create_supabase_service_client(config: AppConfig) -> AsyncClient:
    """Return an async Supabase client using the service role key (bypasses RLS)."""
    if not config.supabase.url or not config.supabase.service_role_key:
        msg = 'Supabase is not configured: url and service_role_key are required.'
        raise RuntimeError(msg)
    return await acreate_client(config.supabase.url, config.supabase.service_role_key)


def create_sync_supabase_service_client(config: AppConfig) -> Client:
    """Return a sync Supabase client using the service role key (bypasses RLS)."""
    if not config.supabase.url or not config.supabase.service_role_key:
        msg = 'Supabase is not configured: url and service_role_key are required.'
        raise RuntimeError(msg)
    return create_client(config.supabase.url, config.supabase.service_role_key)
