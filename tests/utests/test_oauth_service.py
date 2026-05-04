"""Unit tests for OAuth PKCE helpers and response parsing."""

import pytest

from ule.artmentorai_project.services import oauth_service as oauth_service_module
from ule.artmentorai_project.services.oauth_service import generate_pkce_pair


def test_generate_pkce_pair_round_trip_length() -> None:
    verifier, challenge = generate_pkce_pair()
    assert len(verifier) >= 43
    assert challenge != ''
    assert '=' not in challenge


def test_parse_token_payload_flat() -> None:
    data = {
        'access_token': 'a',
        'refresh_token': 'r',
        'expires_in': 42,
        'token_type': 'bearer',
        'user': {'id': 'u1'},
    }
    at, rt, exp, tt, uid = oauth_service_module._parse_token_payload(data)
    assert at == 'a'
    assert rt == 'r'
    assert exp == 42
    assert tt == 'bearer'
    assert uid == 'u1'


def test_parse_token_payload_nested_session() -> None:
    data = {
        'session': {
            'access_token': 'na',
            'refresh_token': 'nr',
            'expires_in': 99,
            'token_type': 'bearer',
        },
        'user': {'id': 'u2'},
    }
    at, rt, exp, _tt, uid = oauth_service_module._parse_token_payload(data)
    assert at == 'na'
    assert rt == 'nr'
    assert exp == 99
    assert uid == 'u2'


def test_parse_token_payload_missing_access_token_raises() -> None:
    with pytest.raises(ValueError, match='missing access_token'):
        oauth_service_module._parse_token_payload({'user': {'id': 'x'}})
