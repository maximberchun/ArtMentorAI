"""Endpoints for private user progress metrics."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ..config import AppConfig
from ..db import create_sync_supabase_service_client
from ..models import AuthUser, ProgressMeResponse, ProgressSnapshotSummary
from ..repositories import ProgressSnapshotRepository, UserProgressRepository
from ..utils.api_errors import SAFE_INTERNAL_ERROR_DETAIL
from .deps import build_current_user_dependency


def create_progress_router(config: AppConfig) -> APIRouter:
    """Create progress router with authenticated user-only endpoints."""
    router = APIRouter(prefix='/progress', tags=['Progress'])
    current_user = build_current_user_dependency(config)

    @router.get(
        '/me',
        summary='Get private progress metrics',
        description='Return XP, level, streak, and recent rubric snapshots for auth user.',
    )
    async def get_progress_me(
        user: Annotated[AuthUser, Depends(current_user)],
    ) -> ProgressMeResponse:
        progress = None
        snapshots = []
        try:
            sb = create_sync_supabase_service_client(config)
            progress_repo = UserProgressRepository(sb, config.logger)
            snapshot_repo = ProgressSnapshotRepository(sb, config.logger)

            progress = progress_repo.get(user.user_id) or progress_repo.default(user.user_id)
            snapshots = snapshot_repo.list_active_for_user(user.user_id, limit=10)
        except RuntimeError as exc:
            if 'PGRST205' in str(exc):
                config.logger.warning(
                    'Progress tables missing in schema cache; returning defaults for user_id=%s',
                    user.user_id,
                )
                progress = UserProgressRepository(
                    create_sync_supabase_service_client(config),
                    config.logger,
                ).default(user.user_id)
                snapshots = []
            else:
                config.logger.exception('Progress load failed for user_id=%s', user.user_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=SAFE_INTERNAL_ERROR_DETAIL,
                ) from exc

        recent_snapshots = [
            ProgressSnapshotSummary(
                id=row.id,
                critique_id=row.critique_id,
                rubric_key=row.rubric_key,
                aggregate_score=row.aggregate_score,
                dimension_scores=getattr(row, 'dimension_scores', {}) or {},
                narrative=getattr(row, 'narrative', None),
                created_at=row.created_at,
            )
            for row in snapshots
        ]

        return ProgressMeResponse(
            user_id=progress.user_id,
            total_xp=progress.total_xp,
            current_level=progress.current_level,
            streak_count=progress.streak_count,
            streak_last_date=progress.streak_last_date,
            badges=progress.badges,
            latest_snapshot=recent_snapshots[0] if recent_snapshots else None,
            recent_snapshots=recent_snapshots,
        )

    return router
