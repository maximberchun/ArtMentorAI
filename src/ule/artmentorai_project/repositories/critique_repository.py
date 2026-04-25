"""Repository for ``public.critiques``."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

from ..models.db_rows import CritiqueRow
from ._rows import as_model, as_model_list, single_row_dict


class CritiqueRepository:
    """Persist critique records (source of truth before vector indexing)."""

    _table = 'critiques'

    def __init__(self, client: Client, logger: logging.Logger | None = None) -> None:
        self._client = client
        self._logger = logger or logging.getLogger(__name__)

    def create(  # noqa: PLR0913
        self,
        *,
        user_id: str,
        summary: str,
        score: int,
        technical_errors: list[str],
        constructive_advice: str,
        tags: list[str] | None = None,
        goals_snapshot: str | None = None,
        conversation_id: str | None = None,
        image_asset_id: str | None = None,
        artwork_filename: str | None = None,
        vector_point_id: str | None = None,
    ) -> CritiqueRow:
        """Insert a critique row."""
        payload: dict[str, Any] = {
            'user_id': user_id,
            'summary': summary,
            'score': score,
            'technical_errors': technical_errors,
            'constructive_advice': constructive_advice,
            'tags': tags or [],
            'goals_snapshot': goals_snapshot,
            'conversation_id': conversation_id,
            'image_asset_id': image_asset_id,
            'artwork_filename': artwork_filename,
            'vector_point_id': vector_point_id,
        }
        try:
            response = self._client.table(self._table).insert(payload).execute()
        except Exception as exc:
            self._logger.exception('Failed to insert critique user_id=%s', user_id)
            msg = f'Failed to save critique: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model(CritiqueRow, single_row_dict(response.data))

    def get_by_id(self, critique_id: str) -> CritiqueRow | None:
        """Return a critique row by primary key (any ``deleted_at``). Internal sync use."""
        try:
            response = (
                self._client.table(self._table).select('*').eq('id', critique_id).limit(1).execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to load critique id=%s', critique_id)
            msg = f'Failed to load critique: {exc!s}'
            raise RuntimeError(msg) from exc

        rows = as_model_list(CritiqueRow, response.data)
        return rows[0] if rows else None

    def get_active(self, critique_id: str, user_id: str) -> CritiqueRow | None:
        """Return a non-deleted critique owned by ``user_id``."""
        try:
            response = (
                self._client.table(self._table)
                .select('*')
                .eq('id', critique_id)
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to load critique id=%s', critique_id)
            msg = f'Failed to load critique: {exc!s}'
            raise RuntimeError(msg) from exc

        rows = as_model_list(CritiqueRow, response.data)
        return rows[0] if rows else None

    def list_active_for_user(self, user_id: str, *, limit: int = 100) -> list[CritiqueRow]:
        """List non-deleted critiques for a user, newest first."""
        try:
            response = (
                self._client.table(self._table)
                .select('*')
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .order('created_at', desc=True)
                .limit(limit)
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to list critiques user_id=%s', user_id)
            msg = f'Failed to list critiques: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model_list(CritiqueRow, response.data)

    def set_vector_point_id(self, critique_id: str, user_id: str, vector_point_id: str) -> None:
        """Attach the derived Qdrant point id after indexing."""
        try:
            self._client.table(self._table).update({'vector_point_id': vector_point_id}).eq(
                'id', critique_id
            ).eq('user_id', user_id).is_('deleted_at', 'null').execute()
        except Exception as exc:
            self._logger.exception('Failed to link vector id for critique id=%s', critique_id)
            msg = f'Failed to update critique vector id: {exc!s}'
            raise RuntimeError(msg) from exc

    def soft_delete(self, critique_id: str, user_id: str) -> bool:
        """Soft-delete a critique if it belongs to ``user_id``."""
        stamp = datetime.now(tz=UTC).isoformat()
        try:
            response = (
                self._client.table(self._table)
                .update({'deleted_at': stamp})
                .eq('id', critique_id)
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .select('id')
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to soft-delete critique id=%s', critique_id)
            msg = f'Failed to delete critique: {exc!s}'
            raise RuntimeError(msg) from exc

        data = response.data
        if isinstance(data, list):
            return len(data) > 0
        return data is not None
