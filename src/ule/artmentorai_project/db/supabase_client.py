"""Supabase client factory for server-side (service role) access."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import AsyncClient, Client

    from ..config import AppConfig


async def create_supabase_service_client(config: AppConfig) -> AsyncClient:
    """Return an async Supabase client using the service role key (bypasses RLS)."""
    if not config.supabase.url or not config.supabase.service_role_key:
        msg = 'Supabase is not configured: url and service_role_key are required.'
        raise RuntimeError(msg)
    try:
        from supabase import acreate_client
    except ImportError as exc:
        msg = (
            'Installed supabase package does not expose async factory `acreate_client`. '
            'Please install a compatible supabase-py version.'
        )
        raise RuntimeError(msg) from exc
    return await acreate_client(config.supabase.url, config.supabase.service_role_key)


def create_sync_supabase_service_client(config: AppConfig) -> Client:
    """Return a sync Supabase client using the service role key (bypasses RLS)."""
    if not config.supabase.url or not config.supabase.service_role_key:
        msg = 'Supabase is not configured: url and service_role_key are required.'
        raise RuntimeError(msg)
    try:
        from supabase import create_client
    except ImportError as exc:
        msg = (
            'Installed supabase package does not expose sync factory `create_client`. '
            'Please install a compatible supabase-py version.'
        )
        raise RuntimeError(msg) from exc
    return create_client(config.supabase.url, config.supabase.service_role_key)
