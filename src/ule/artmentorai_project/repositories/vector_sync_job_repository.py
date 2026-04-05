"""Repository for ``public.vector_sync_jobs`` (Postgres → Qdrant outbox)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

from ..models.db_rows import VectorSyncJobRow
from ._rows import as_model, as_model_list, single_row_dict

ENTITY_CRITIQUE = 'critique'
ENTITY_PORTFOLIO_ITEM = 'portfolio_item'
OP_UPSERT = 'upsert'
OP_DELETE = 'delete'


class VectorSyncJobRepository:
    """Enqueue and claim idempotent vector sync jobs (service role)."""

    _table = 'vector_sync_jobs'

    def __init__(self, client: Client, logger: logging.Logger | None = None) -> None:
        self._client = client
        self._logger = logger or logging.getLogger(__name__)

    def enqueue(self, entity_kind: str, entity_id: str, operation: str) -> None:
        """Atomically enqueue via ``enqueue_vector_sync`` (coalesces pending upserts)."""
        try:
            self._client.rpc(
                'enqueue_vector_sync',
                {
                    'p_entity_kind': entity_kind,
                    'p_entity_id': entity_id,
                    'p_operation': operation,
                },
            ).execute()
        except Exception as exc:
            self._logger.exception(
                'Failed to enqueue vector sync kind=%s id=%s op=%s',
                entity_kind,
                entity_id,
                operation,
            )
            msg = f'Failed to enqueue vector sync job: {exc!s}'
            raise RuntimeError(msg) from exc

    def fetch_pending_ready(self, *, limit: int, now_iso: str) -> list[VectorSyncJobRow]:
        """List pending jobs due for processing (not yet claimed)."""
        try:
            response = (
                self._client.table(self._table)
                .select('*')
                .eq('status', 'pending')
                .lte('next_attempt_at', now_iso)
                .order('created_at')
                .limit(limit)
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to list pending vector sync jobs')
            msg = f'Failed to list vector sync jobs: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model_list(VectorSyncJobRow, response.data)

    def try_claim(self, job_id: str) -> VectorSyncJobRow | None:
        """Move one job from ``pending`` → ``processing``. Returns row if this worker won."""
        try:
            response = (
                self._client.table(self._table)
                .update({'status': 'processing'})
                .eq('id', job_id)
                .eq('status', 'pending')
                .select('*')
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to claim vector sync job id=%s', job_id)
            msg = f'Failed to claim vector sync job: {exc!s}'
            raise RuntimeError(msg) from exc

        data = response.data
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            return as_model(VectorSyncJobRow, data[0])
        return None

    def complete_and_remove(self, job_id: str) -> None:
        """Drop a successfully processed job row."""
        try:
            self._client.table(self._table).delete().eq('id', job_id).execute()
        except Exception as exc:
            self._logger.exception('Failed to remove completed vector sync job id=%s', job_id)
            msg = f'Failed to remove vector sync job: {exc!s}'
            raise RuntimeError(msg) from exc

    def schedule_retry(self, job: VectorSyncJobRow, error: str, *, max_attempts: int) -> None:
        """Return job to ``pending`` with backoff, or mark ``dead_letter``."""
        attempts = job.attempt_count + 1
        err_short = (error or '')[:4000]
        if attempts >= max_attempts:
            self._dead_letter(job.id, attempts, err_short)
            return
        delay_sec = min(300, 2 ** min(attempts, 8))
        next_at = datetime.now(tz=UTC) + timedelta(seconds=delay_sec)
        payload: dict[str, Any] = {
            'status': 'pending',
            'attempt_count': attempts,
            'last_error': err_short,
            'next_attempt_at': next_at.isoformat(),
        }
        try:
            self._client.table(self._table).update(payload).eq('id', job.id).eq(
                'status', 'processing'
            ).execute()
        except Exception as exc:
            self._logger.exception('Failed to schedule retry for vector sync job id=%s', job.id)
            msg = f'Failed to schedule vector sync retry: {exc!s}'
            raise RuntimeError(msg) from exc

    def _dead_letter(self, job_id: str, attempts: int, err_short: str) -> None:
        try:
            self._client.table(self._table).update(
                {
                    'status': 'dead_letter',
                    'attempt_count': attempts,
                    'last_error': err_short,
                }
            ).eq('id', job_id).eq('status', 'processing').execute()
        except Exception as exc:
            self._logger.exception('Failed to dead-letter vector sync job id=%s', job_id)
            msg = f'Failed to mark vector sync dead letter: {exc!s}'
            raise RuntimeError(msg) from exc

    def release_stale_processing(self, *, older_than_iso: str) -> None:
        """Recover jobs stuck in ``processing`` (e.g. worker crash)."""
        try:
            self._client.table(self._table).update({'status': 'pending'}).eq('status', 'processing').lt(
                'updated_at', older_than_iso
            ).execute()
        except Exception as exc:
            self._logger.exception('Failed to release stale vector sync jobs')
            msg = f'Failed to release stale vector sync jobs: {exc!s}'
            raise RuntimeError(msg) from exc
