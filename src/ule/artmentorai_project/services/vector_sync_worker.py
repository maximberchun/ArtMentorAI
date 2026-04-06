"""Background worker: process ``vector_sync_jobs`` → Qdrant (retries, idempotent upserts)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from ..db.supabase_client import create_supabase_service_client
from ..models.db_rows import CritiqueRow, VectorSyncJobRow
from ..repositories import (
    CritiqueRepository,
    ImageAssetRepository,
    PortfolioItemRepository,
    ProfileRepository,
    VectorSyncJobRepository,
)
from ..repositories.vector_sync_job_repository import (
    ENTITY_CRITIQUE,
    ENTITY_PORTFOLIO_ITEM,
    OP_DELETE,
    OP_UPSERT,
)
from .vector_service import ArtCritique, PortfolioRecord, VectorService

from ..config import AppConfig


def _technical_errors_as_str_list(raw: list[Any]) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def _critique_from_row(row: CritiqueRow) -> ArtCritique:
    critique = ArtCritique(
        summary=row.summary,
        score=row.score,
        technical_errors=_technical_errors_as_str_list(row.technical_errors),
        constructive_advice=row.constructive_advice,
        tags=row.tags,
        goals_snapshot=row.goals_snapshot,
    )
    if row.created_at is not None:
        critique.timestamp = row.created_at.isoformat()
    return critique


class VectorSyncWorker:
    """Polls Postgres outbox and applies upserts/deletes to Qdrant."""

    def __init__(
        self,
        config: AppConfig,
        *,
        poll_interval_sec: float = 2.0,
        batch_size: int = 10,
        max_attempts: int = 5,
        stale_processing_minutes: int = 30,
    ) -> None:
        self._config = config
        self._logger = config.logger
        self._poll_interval_sec = poll_interval_sec
        self._batch_size = batch_size
        self._max_attempts = max_attempts
        self._stale_processing_minutes = stale_processing_minutes
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._vector: VectorService | None = None
        self._vector_failed_logged = False

    async def start(self) -> None:
        """Start background polling task."""
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop(), name='vector_sync_worker')

    async def stop(self) -> None:
        """Signal shutdown and wait for the task."""
        self._stop.set()
        if self._task is None:
            return
        t = self._task
        self._task = None
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass

    async def _run_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.to_thread(self._run_batch)
            except Exception:
                self._logger.exception('Vector sync worker batch crashed')
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._poll_interval_sec)
            except asyncio.TimeoutError:
                pass

    def _ensure_vector(self) -> VectorService | None:
        if self._vector is not None:
            return self._vector
        try:
            self._vector = VectorService(config=self._config, logger=self._logger)
        except RuntimeError as e:
            if not self._vector_failed_logged:
                self._logger.warning(
                    'Vector sync worker: VectorService unavailable (%s). Jobs will retry.',
                    e,
                )
                self._vector_failed_logged = True
            return None
        self._vector_failed_logged = False
        return self._vector

    def _run_batch(self) -> None:
        try:
            sb = create_supabase_service_client(self._config)
        except RuntimeError as e:
            self._logger.debug('Vector sync worker: Supabase not configured: %s', e)
            return

        jobs = VectorSyncJobRepository(sb, self._logger)
        stale_cutoff = (
            datetime.now(tz=UTC) - timedelta(minutes=self._stale_processing_minutes)
        ).isoformat()
        jobs.release_stale_processing(older_than_iso=stale_cutoff)

        now_iso = datetime.now(tz=UTC).isoformat()
        candidates = jobs.fetch_pending_ready(limit=self._batch_size, now_iso=now_iso)
        vector = self._ensure_vector()
        if vector is None:
            return

        for cand in candidates:
            claimed = jobs.try_claim(cand.id)
            if claimed is None:
                continue
            self._process_one(
                vector=vector,
                job=claimed,
                sb=sb,
                jobs_repo=jobs,
            )

    def _process_one(
        self,
        *,
        vector: VectorService,
        job: VectorSyncJobRow,
        sb: Any,
        jobs_repo: VectorSyncJobRepository,
    ) -> None:
        try:
            if job.entity_kind == ENTITY_CRITIQUE:
                self._process_critique(vector, job, sb)
            elif job.entity_kind == ENTITY_PORTFOLIO_ITEM:
                self._process_portfolio_item(vector, job, sb)
            else:
                msg = f'unknown entity_kind {job.entity_kind}'
                raise RuntimeError(msg)
        except Exception as e:  # noqa: BLE001
            err = f'{type(e).__name__}: {e!s}'
            will_dead_letter = job.attempt_count + 1 >= self._max_attempts
            if will_dead_letter:
                self._logger.error(
                    'Vector sync job dead-lettered id=%s kind=%s entity=%s op=%s error=%s',
                    job.id,
                    job.entity_kind,
                    job.entity_id,
                    job.operation,
                    err,
                )
            else:
                self._logger.warning(
                    'Vector sync job failed id=%s kind=%s entity=%s op=%s: %s',
                    job.id,
                    job.entity_kind,
                    job.entity_id,
                    job.operation,
                    err,
                )
            jobs_repo.schedule_retry(job, err, max_attempts=self._max_attempts)
            return

        jobs_repo.complete_and_remove(job.id)

    def _retain_memory(self, profile_repo: ProfileRepository, user_id: str) -> bool:
        row = profile_repo.get_active(user_id)
        if row is None:
            return True
        return row.retain_memory

    def _process_critique(
        self,
        vector: VectorService,
        job: VectorSyncJobRow,
        sb: Any,
    ) -> None:
        critique_repo = CritiqueRepository(sb, self._logger)
        profile_repo = ProfileRepository(sb, self._logger)
        image_repo = ImageAssetRepository(sb, self._logger)
        row = critique_repo.get_by_id(job.entity_id)
        if row is None:
            return

        point_id = row.vector_point_id or row.id

        if job.operation == OP_DELETE:
            vector.delete_points_by_ids([point_id])
            return

        if job.operation != OP_UPSERT:
            msg = f'unsupported operation {job.operation}'
            raise RuntimeError(msg)

        if row.deleted_at is not None:
            vector.delete_points_by_ids([point_id])
            return

        if not self._retain_memory(profile_repo, row.user_id):
            vector.delete_points_by_ids([point_id])
            return

        image_path: str | None = None
        if row.image_asset_id:
            asset = image_repo.get_by_id(row.image_asset_id)
            if asset is not None and asset.deleted_at is None:
                image_path = asset.storage_object_path

        critique = _critique_from_row(row)
        filename = row.artwork_filename or 'unknown'
        vector.upsert_critique_with_stable_id(
            row.id,
            critique,
            filename,
            row.user_id,
            image_path,
            row.id,
        )
        critique_repo.set_vector_point_id(row.id, row.user_id, row.id)

    def _process_portfolio_item(
        self,
        vector: VectorService,
        job: VectorSyncJobRow,
        sb: Any,
    ) -> None:
        portfolio_repo = PortfolioItemRepository(sb, self._logger)
        profile_repo = ProfileRepository(sb, self._logger)
        image_repo = ImageAssetRepository(sb, self._logger)
        row = portfolio_repo.get_by_id(job.entity_id)
        if row is None:
            return

        point_id = row.vector_point_id or row.id

        if job.operation == OP_DELETE:
            vector.delete_points_by_ids([point_id])
            return

        if job.operation != OP_UPSERT:
            msg = f'unsupported operation {job.operation}'
            raise RuntimeError(msg)

        if row.deleted_at is not None:
            vector.delete_points_by_ids([point_id])
            return

        if not self._retain_memory(profile_repo, row.user_id):
            vector.delete_points_by_ids([point_id])
            return

        asset = image_repo.get_by_id(row.image_asset_id)
        image_path = (
            asset.storage_object_path
            if asset is not None and asset.deleted_at is None
            else None
        )
        record = PortfolioRecord(
            filename=row.filename,
            user_id=row.user_id,
            tags=row.tags,
            description=row.description,
            image_path=image_path,
        )
        if row.created_at is not None:
            record.timestamp = row.created_at.isoformat()

        vector.upsert_portfolio_with_stable_id(row.id, record, row.id)
        portfolio_repo.set_vector_point_id(row.id, row.user_id, row.id)
