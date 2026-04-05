"""Database client factories (Supabase / Postgres via PostgREST)."""

from .supabase_client import create_supabase_service_client

__all__ = [
    'create_supabase_service_client',
]
