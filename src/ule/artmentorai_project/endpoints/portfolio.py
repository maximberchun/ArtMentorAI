"""Endpoints for portfolio upload and history.

This module provides REST endpoints for:
- Bulk upload of portfolio images (Postgres + async Qdrant sync)
- Retrieving user history (critiques and portfolio items)
- Retrieving a single item by ID
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..db.supabase_client import create_supabase_service_client
from ..models import AuthUser, PortfolioHistoryItem, PortfolioUploadResponse
from ..repositories import ImageAssetRepository, PortfolioItemRepository, VectorSyncJobRepository
from ..repositories.vector_sync_job_repository import ENTITY_PORTFOLIO_ITEM, OP_UPSERT
from ..services import StorageService, VectorService
from ..services.auth_service import AuthService
from ..services.vector_service import PortfolioRecord
from ..utils.upload_validation import (
    validate_file_size,
    validate_image_content_type,
    validate_image_file,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from ..config import AppConfig
    from ..models.db_rows import PortfolioItemRow

_bearer = HTTPBearer(auto_error=True)


def _build_current_user_dependency(config: AppConfig) -> Callable[..., Awaitable[AuthUser]]:
    auth = AuthService(config)

    async def _current_user(
        creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    ) -> AuthUser:
        return await auth.verify_access_token(creds.credentials)

    return _current_user


def get_vector_service(config: AppConfig) -> VectorService | None:
    """Get VectorService; returns None if Qdrant is unavailable."""
    try:
        return VectorService(
            host='localhost',
            port=6333,
            logger=config.logger,
        )
    except RuntimeError as init_error:
        config.logger.warning(
            'VectorService unavailable: %s. Portfolio endpoints will fail.',
            str(init_error),
        )
        return None


def _parse_tags(tags: str | None) -> list[str]:
    """Parse comma-separated tags string into a list of non-empty strings."""
    return [t.strip() for t in (tags or '').split(',') if t.strip()]


def _require_filename(upload_file: UploadFile) -> str:
    """Return file name or raise HTTP 400 when omitted."""
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Each file must have a filename.',
        )
    return upload_file.filename


async def _validate_and_build_records(
    files: list[UploadFile],
    user_id: str,
    tag_list: list[str],
    config: AppConfig,
    storage_service: StorageService,
) -> list[PortfolioRecord]:
    """Validate uploaded files and build PortfolioRecords. Raises HTTPException on error."""
    records: list[PortfolioRecord] = []
    uploaded_paths: list[str] = []
    try:
        for f in files:
            filename = _require_filename(f)
            mime = validate_image_content_type(f.content_type)
            content = await f.read()
            validate_file_size(content, config.upload.max_file_size_mb)
            validate_image_file(filename, mime, config)
            image_path = storage_service.upload_image(
                user_id=user_id,
                image_bytes=content,
                filename=filename,
                mime_type=mime,
            )
            uploaded_paths.append(image_path)
            records.append(
                PortfolioRecord(
                    filename=filename,
                    user_id=user_id,
                    tags=tag_list,
                    description=None,
                    image_path=image_path,
                )
            )
    except HTTPException:
        for path in uploaded_paths:
            storage_service.delete_file(path)
        raise
    except RuntimeError as e:
        for path in uploaded_paths:
            storage_service.delete_file(path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to upload image(s): {e!s}',
        ) from e
    return records


def _get_item_or_raise(svc: VectorService, storage_service: StorageService, item_id: str) -> dict:
    """Return item by id or raise 404."""
    item = svc.get_point_by_id(
        item_id,
        signed_url_resolver=storage_service.create_signed_url,
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Item not found',
        )
    return item


def create_portfolio_router(config: AppConfig) -> APIRouter:  # noqa: C901, PLR0915
    """
    Create router for portfolio upload and history.

    Upload persists to Postgres and enqueues Qdrant sync; history/item reads
    require VectorService and return 503 if Qdrant is unavailable.
    """
    router = APIRouter(
        prefix='/portfolio',
        tags=['Portfolio'],
        responses={
            400: {'description': 'Invalid file or request'},
            404: {'description': 'Item not found'},
            413: {'description': 'File too large'},
            415: {'description': 'Unsupported media type'},
            503: {'description': 'Vector database unavailable'},
        },
    )

    try:
        vector_service: VectorService | None = get_vector_service(config)
    except Exception:
        config.logger.exception('Failed to get vector service')
        vector_service = None
    try:
        storage_service = StorageService(config)
    except RuntimeError:
        config.logger.exception('Failed to initialize storage service')
        storage_service = None
    current_user = _build_current_user_dependency(config)

    def _require_vector_service() -> VectorService:
        if vector_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Portfolio storage is temporarily unavailable.',
            )
        return vector_service

    def _require_storage_service() -> StorageService:
        if storage_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Image storage is temporarily unavailable.',
            )
        return storage_service

    @router.post(
        '/upload',
        summary='Upload portfolio images',
        description=(
            "Upload one or more images to the user's portfolio. "
            'Persisted in Postgres and indexed to Qdrant asynchronously (no auto-critique). '
            'Optional tags are applied to all uploaded files.'
        ),
    )
    async def upload_portfolio(  # noqa: C901
        files: Annotated[
            list[UploadFile],
            File(description='Image files to add to the portfolio.'),
        ],
        user: Annotated[AuthUser, Depends(current_user)],
        tags: Annotated[
            str | None,
            Form(description='Optional comma-separated tags applied to all files.'),
        ] = None,
    ) -> PortfolioUploadResponse:  # pyright: ignore[reportUnusedFunction]
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='At least one file is required.',
            )
        storage = _require_storage_service()
        records = await _validate_and_build_records(
            files,
            user.user_id,
            _parse_tags(tags),
            config,
            storage,
        )
        try:
            sb = create_supabase_service_client(config)
        except RuntimeError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f'Database is not configured or unavailable: {e!s}',
            ) from e

        image_repo = ImageAssetRepository(sb, config.logger)
        portfolio_repo = PortfolioItemRepository(sb, config.logger)
        sync_repo = VectorSyncJobRepository(sb, config.logger)

        created_rows: list[PortfolioItemRow] = []

        def _missing_storage_path() -> None:
            msg = 'Missing storage path after upload.'
            raise RuntimeError(msg)

        try:
            for record in records:
                if not record.image_path:
                    _missing_storage_path()
                asset = image_repo.create(
                    user_id=user.user_id,
                    storage_bucket=config.supabase.storage_bucket,
                    storage_object_path=record.image_path,
                    mime_type=None,
                    original_filename=record.filename,
                    byte_size=None,
                )
                row = portfolio_repo.create(
                    user_id=user.user_id,
                    image_asset_id=asset.id,
                    filename=record.filename,
                    tags=record.tags,
                    description=record.description,
                )
                sync_repo.enqueue(ENTITY_PORTFOLIO_ITEM, row.id, OP_UPSERT)
                created_rows.append(row)
        except HTTPException:
            raise
        except Exception as e:
            for row in reversed(created_rows):
                portfolio_repo.soft_delete(row.id, row.user_id)
                image_repo.soft_delete(row.image_asset_id, row.user_id)
            for rec in records:
                if rec.image_path:
                    storage.delete_file(rec.image_path)
            config.logger.exception('Failed to persist portfolio for user_id=%s', user.user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to save portfolio: {e!s}',
            ) from e

        return PortfolioUploadResponse(ids=[r.id for r in created_rows])

    @router.get(
        '/history/me',
        summary='Get user portfolio and critique history',
        description=(
            'Returns a list of stored items (critiques and portfolio items) '
            'for the current user, newest first. Optional type filter: critique or portfolio_item.'
        ),
    )
    async def get_history(
        user: Annotated[AuthUser, Depends(current_user)],
        limit: Annotated[
            int,
            Query(description='Max number of items to return', ge=1, le=500),
        ] = 100,
        type_filter: Annotated[
            str | None,
            Query(description='Filter by type: critique or portfolio_item'),
        ] = None,
    ) -> list[PortfolioHistoryItem]:
        svc = _require_vector_service()
        storage = _require_storage_service()
        try:
            raw = svc.search_user_history(
                user_id=user.user_id,
                limit=limit,
                type_filter=type_filter,
                signed_url_resolver=storage.create_signed_url,
            )
        except RuntimeError as e:
            config.logger.exception('Failed to get history for user_id=%s', user.user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to retrieve history: {e!s}',
            ) from e
        return [PortfolioHistoryItem.model_validate(r) for r in raw]

    @router.get(
        '/item/{item_id}',
        summary='Get a single portfolio or critique item by ID',
        description='Returns full details (payload) for one stored item.',
    )
    async def get_item(
        item_id: str, user: Annotated[AuthUser, Depends(current_user)]
    ) -> PortfolioHistoryItem:  # pyright: ignore[reportUnusedFunction]
        svc = _require_vector_service()
        storage = _require_storage_service()
        payload = _get_item_or_raise(svc, storage, item_id)
        if payload.get('user_id') != user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Item not found')
        return PortfolioHistoryItem.model_validate(payload)

    # Backward-compatible endpoint (deprecated).
    @router.get(
        '/history/{user_id}',
        summary='Get user history (deprecated)',
        description='Deprecated. Use GET /portfolio/history/me. Only allowed for the current user.',
        deprecated=True,
    )
    async def get_history_deprecated(
        user_id: str,
        user: Annotated[AuthUser, Depends(current_user)],
        limit: Annotated[
            int,
            Query(description='Max number of items to return', ge=1, le=500),
        ] = 100,
        type_filter: Annotated[
            str | None,
            Query(description='Filter by type: critique or portfolio_item'),
        ] = None,
    ) -> list[PortfolioHistoryItem]:
        if user_id != user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden')
        return await get_history(user=user, limit=limit, type_filter=type_filter)

    return router
