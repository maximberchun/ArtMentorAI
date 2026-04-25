"""Repository for ``public.conversation_messages``."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

from ..models.db_rows import ConversationMessageRow
from ._rows import as_model, as_model_list, single_row_dict

_VALID_ROLES = {'user', 'assistant', 'system'}


class ConversationMessageRepository:
    """Persist and query messages within a conversation thread."""

    _table = 'conversation_messages'

    def __init__(self, client: Client, logger: logging.Logger | None = None) -> None:
        self._client = client
        self._logger = logger or logging.getLogger(__name__)

    def create(
        self,
        *,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        critique_id: str | None = None,
    ) -> ConversationMessageRow:
        """Insert a conversation message row."""
        normalized_role = role.strip().lower()
        if normalized_role not in _VALID_ROLES:
            msg = f'Invalid conversation role: {role}'
            raise ValueError(msg)

        payload: dict[str, Any] = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'role': normalized_role,
            'content': content,
            'critique_id': critique_id,
        }
        try:
            response = self._client.table(self._table).insert(payload).execute()
        except Exception as exc:
            self._logger.exception(
                'Failed to insert conversation message conversation_id=%s user_id=%s',
                conversation_id,
                user_id,
            )
            msg = f'Failed to save conversation message: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model(ConversationMessageRow, single_row_dict(response.data))

    def list_recent_for_conversation(
        self,
        *,
        conversation_id: str,
        user_id: str,
        limit: int = 8,
    ) -> list[ConversationMessageRow]:
        """List newest active messages for one user conversation."""
        safe_limit = max(1, min(limit, 20))
        try:
            response = (
                self._client.table(self._table)
                .select('*')
                .eq('conversation_id', conversation_id)
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .order('created_at', desc=True)
                .limit(safe_limit)
                .execute()
            )
        except Exception as exc:
            self._logger.exception(
                'Failed to list conversation messages conversation_id=%s user_id=%s',
                conversation_id,
                user_id,
            )
            msg = f'Failed to list conversation messages: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model_list(ConversationMessageRow, response.data)
