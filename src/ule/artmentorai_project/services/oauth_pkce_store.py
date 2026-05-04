"""In-memory store for OAuth PKCE sessions (state → code_verifier).

Used to bind Supabase OAuth callbacks to the server instance that started the
flow. Suitable for single-process deployments; use a shared store if you run
multiple API workers.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _PendingOAuth:
    code_verifier: str
    created_at: float


class OAuthPkceStore:
    """TTL map from OAuth ``state`` to ``code_verifier``."""

    def __init__(self, ttl_seconds: float = 600.0) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._sessions: dict[str, _PendingOAuth] = {}

    def remember(self, state: str, code_verifier: str) -> None:
        """Record a pending flow; overwrites any existing entry for ``state``."""
        with self._lock:
            self._prune_locked()
            self._sessions[state] = _PendingOAuth(
                code_verifier=code_verifier,
                created_at=time.monotonic(),
            )

    def pop_verifier(self, state: str) -> str | None:
        """Return the verifier for ``state`` if valid, then remove it (one-time use)."""
        with self._lock:
            self._prune_locked()
            pending = self._sessions.pop(state, None)
            if pending is None:
                return None
            if time.monotonic() - pending.created_at > self._ttl:
                return None
            return pending.code_verifier

    def _prune_locked(self) -> None:
        now = time.monotonic()
        expired = [k for k, v in self._sessions.items() if now - v.created_at > self._ttl]
        for key in expired:
            del self._sessions[key]
