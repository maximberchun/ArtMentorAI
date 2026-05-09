"""Supabase client factory for server-side (service role) access."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from postgrest.constants import DEFAULT_POSTGREST_CLIENT_TIMEOUT
from supabase.lib.client_options import AsyncClientOptions, SyncClientOptions

if TYPE_CHECKING:
    from supabase import AsyncClient, Client

    from ..config import AppConfig


def _require_supabase_config(config: AppConfig) -> tuple[str, str]:
    """Return validated Supabase URL + service role key."""
    if not config.supabase.url or not config.supabase.service_role_key:
        msg = 'Supabase is not configured: url and service_role_key are required.'
        raise RuntimeError(msg)
    return config.supabase.url, config.supabase.service_role_key


def _raise_client_import_error(client_type: str, factory_name: str, exc: ImportError) -> None:
    """Raise a normalized error for incompatible supabase-py installs."""
    msg = (
        f'Installed supabase package does not expose {client_type} factory `{factory_name}`. '
        'Please install a compatible supabase-py version.'
    )
    raise RuntimeError(msg) from exc


def _service_role_httpx_timeout() -> httpx.Timeout:
    return httpx.Timeout(DEFAULT_POSTGREST_CLIENT_TIMEOUT)


def _sync_service_client_options() -> SyncClientOptions:
    """PostgREST defaults to HTTP/2; Supabase edge often drops HTTP/2 mid-request."""
    return SyncClientOptions(
        httpx_client=httpx.Client(
            timeout=_service_role_httpx_timeout(),
            follow_redirects=True,
            http2=False,
        )
    )


def _async_service_client_options() -> AsyncClientOptions:
    return AsyncClientOptions(
        httpx_client=httpx.AsyncClient(
            timeout=_service_role_httpx_timeout(),
            follow_redirects=True,
            http2=False,
        )
    )


async def create_supabase_service_client(config: AppConfig) -> AsyncClient:
    """Return an async Supabase client using the service role key (bypasses RLS)."""
    url, service_role_key = _require_supabase_config(config)
    try:
        from supabase import acreate_client  # noqa: PLC0415
    except ImportError as exc:
        _raise_client_import_error('async', 'acreate_client', exc)
    return await acreate_client(url, service_role_key, _async_service_client_options())


def create_sync_supabase_service_client(config: AppConfig) -> Client:
    """Return a sync Supabase client using the service role key (bypasses RLS)."""
    url, service_role_key = _require_supabase_config(config)
    try:
        from supabase import create_client  # noqa: PLC0415
    except ImportError as exc:
        _raise_client_import_error('sync', 'create_client', exc)
    return create_client(url, service_role_key, _sync_service_client_options())
