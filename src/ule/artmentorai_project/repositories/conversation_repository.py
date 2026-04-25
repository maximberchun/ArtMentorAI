"""Repository for ``public.conversations``."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

from ..models.db_rows import ConversationRow
from ._rows import as_model, as_model_list, single_row_dict


class ConversationRepository:
    """Persist and query user conversation threads."""

    _table = 'conversations'

    def __init__(self, client: Client, logger: logging.Logger | None = None) -> None:
        self._client = client
        self._logger = logger or logging.getLogger(__name__)

    def create(self, *, user_id: str, title: str | None = None) -> ConversationRow:
        """Insert a new conversation row."""
        payload: dict[str, Any] = {'user_id': user_id, 'title': title}
        try:
            response = self._client.table(self._table).insert(payload).execute()
        except Exception as exc:
            self._logger.exception('Failed to create conversation user_id=%s', user_id)
            msg = f'Failed to create conversation: {exc!s}'
            raise RuntimeError(msg) from exc
        return as_model(ConversationRow, single_row_dict(response.data))

    def get_active_for_user(self, conversation_id: str, user_id: str) -> ConversationRow | None:
        """Return a non-deleted conversation owned by ``user_id``."""
        try:
            response = (
                self._client.table(self._table)
                .select('*')
                .eq('id', conversation_id)
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to load conversation id=%s user_id=%s', conversation_id, user_id)
            msg = f'Failed to load conversation: {exc!s}'
            raise RuntimeError(msg) from exc

        rows = as_model_list(ConversationRow, response.data)
        return rows[0] if rows else None
