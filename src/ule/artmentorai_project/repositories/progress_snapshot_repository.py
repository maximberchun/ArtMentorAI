"""Repository for ``public.progress_snapshots``."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

from ..models.db_rows import ProgressSnapshotRow
from ._rows import as_model, as_model_list, postgrest_returned_rows, single_row_dict


class ProgressSnapshotRepository:
    """Structured progress / rubric scores tied to critiques (optional)."""

    _table = 'progress_snapshots'

    def __init__(self, client: Client, logger: logging.Logger | None = None) -> None:
        self._client = client
        self._logger = logger or logging.getLogger(__name__)

    def create(  # noqa: PLR0913
        self,
        *,
        user_id: str,
        rubric_key: str,
        rubric_version: str = '1.0',
        dimension_scores: dict[str, Any] | None = None,
        aggregate_score: float | None = None,
        narrative: str | None = None,
        critique_id: str | None = None,
    ) -> ProgressSnapshotRow:
        """Insert one progress snapshot row."""
        payload: dict[str, Any] = {
            'user_id': user_id,
            'rubric_key': rubric_key,
            'rubric_version': rubric_version,
            'dimension_scores': dimension_scores or {},
            'aggregate_score': aggregate_score,
            'narrative': narrative,
            'critique_id': critique_id,
        }
        try:
            response = self._client.table(self._table).insert(payload).execute()
        except Exception as exc:
            self._logger.exception('Failed to insert progress_snapshot user_id=%s', user_id)
            msg = f'Failed to save progress snapshot: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model(ProgressSnapshotRow, single_row_dict(response.data))

    def get_active(self, snapshot_id: str, user_id: str) -> ProgressSnapshotRow | None:
        """Return a non-deleted snapshot owned by ``user_id``."""
        try:
            response = (
                self._client.table(self._table)
                .select('*')
                .eq('id', snapshot_id)
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to load progress_snapshot id=%s', snapshot_id)
            msg = f'Failed to load progress snapshot: {exc!s}'
            raise RuntimeError(msg) from exc

        rows = as_model_list(ProgressSnapshotRow, response.data)
        return rows[0] if rows else None

    def list_active_for_user(self, user_id: str, *, limit: int = 100) -> list[ProgressSnapshotRow]:
        """List non-deleted snapshots for a user, newest first."""
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
            self._logger.exception('Failed to list progress_snapshots user_id=%s', user_id)
            msg = f'Failed to list progress snapshots: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model_list(ProgressSnapshotRow, response.data)

    def soft_delete(self, snapshot_id: str, user_id: str) -> bool:
        """Soft-delete a snapshot if it belongs to ``user_id``."""
        stamp = datetime.now(tz=UTC).isoformat()
        try:
            response = (
                self._client.table(self._table)
                .update({'deleted_at': stamp})
                .eq('id', snapshot_id)
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .select('id')
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to soft-delete progress_snapshot id=%s', snapshot_id)
            msg = f'Failed to delete progress snapshot: {exc!s}'
            raise RuntimeError(msg) from exc

        return postgrest_returned_rows(response.data)
