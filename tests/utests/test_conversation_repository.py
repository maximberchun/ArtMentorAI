"""Unit tests for conversation repositories."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ule.artmentorai_project.repositories.conversation_message_repository import (
    ConversationMessageRepository,
)
from ule.artmentorai_project.repositories.conversation_repository import ConversationRepository


def test_conversation_message_create_rejects_invalid_role() -> None:
    """Conversation message repository should reject unknown roles before DB write."""
    repo = ConversationMessageRepository(MagicMock())

    with pytest.raises(ValueError, match='Invalid conversation role'):
        repo.create(conversation_id='conv-1', user_id='user-1', role='moderator', content='hello')


def test_conversation_get_active_returns_none_for_empty_result() -> None:
    """Conversation repository should return None when no active row is found."""
    client = MagicMock()
    repo = ConversationRepository(client)
    (
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.limit.return_value.execute.return_value
    ) = SimpleNamespace(data=[])

    result = repo.get_active_for_user('conv-1', 'user-1')

    assert result is None
