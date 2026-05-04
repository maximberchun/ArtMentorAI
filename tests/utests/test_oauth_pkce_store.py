"""Tests for OAuth PKCE session store."""

import time

from ule.artmentorai_project.services.oauth_pkce_store import OAuthPkceStore


def test_pop_verifier_returns_verifier_once() -> None:
    store = OAuthPkceStore(ttl_seconds=60.0)
    store.remember('state-1', 'verifier-secret')
    assert store.pop_verifier('state-1') == 'verifier-secret'
    assert store.pop_verifier('state-1') is None


def test_pop_verifier_unknown_state() -> None:
    store = OAuthPkceStore()
    assert store.pop_verifier('missing') is None


def test_expired_session_is_rejected() -> None:
    store = OAuthPkceStore(ttl_seconds=0.01)
    store.remember('s', 'v')
    time.sleep(0.02)
    assert store.pop_verifier('s') is None
