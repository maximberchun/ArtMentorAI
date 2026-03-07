"""Endpoints for portfolio upload and history.

This module provides REST endpoints for:
- Bulk upload of portfolio images (stored in Qdrant as portfolio_item)
- Retrieving user history (critiques and portfolio items)
- Retrieving a single item by ID
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from ..config import AppConfig
from ..services import VectorService
from ..services.vector_service import PortfolioRecord
from ..utils.upload_validation import (
    validate_file_size,
    validate_image_content_type,
    validate_image_file,
)


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


async def _validate_and_build_records(
    files: list[UploadFile],
    user_id: str,
    tag_list: list[str],
    config: AppConfig,
) -> list[PortfolioRecord]:
    """Validate uploaded files and build PortfolioRecords. Raises HTTPException on error."""
    records: list[PortfolioRecord] = []
    for f in files:
        if not f.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Each file must have a filename.',
            )
        mime = validate_image_content_type(f.content_type)
        content = await f.read()
        validate_file_size(content, config.upload.max_file_size_mb)
        validate_image_file(f.filename or 'unknown', mime, config)
        records.append(
            PortfolioRecord(
                filename=f.filename,
                user_id=user_id,
                tags=tag_list,
                description=None,
            )
        )
    return records


def _fetch_user_history(
    svc: VectorService,
    user_id: str,
    limit: int,
    type_filter: str | None,
    config: AppConfig,
) -> list[dict]:
    """Call vector service and raise HTTPException on failure."""
    try:
        return svc.search_user_history(
            user_id=user_id,
            limit=limit,
            type_filter=type_filter,
        )
    except RuntimeError as e:
        config.logger.exception('Failed to get history for user_id=%s', user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to retrieve history: {e!s}',
        ) from e


def _get_item_or_raise(svc: VectorService, item_id: str) -> dict:
    """Return item by id or raise 404."""
    item = svc.get_point_by_id(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Item not found',
        )
    return item


def create_portfolio_router(config: AppConfig) -> APIRouter:
    """
    Create router for portfolio upload and history.

    Requires VectorService (Qdrant). Endpoints return 503 if the vector DB
    is unavailable.
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

    def _require_vector_service() -> VectorService:
        if vector_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Portfolio storage is temporarily unavailable.',
            )
        return vector_service

    @router.post(
        '/upload',
        summary='Upload portfolio images',
        description=(
            'Upload one or more images to the user\'s portfolio. '
            'Stored in the vector DB as portfolio_item (no auto-critique). '
            'Optional tags are applied to all uploaded files.'
        ),
    )
    async def upload_portfolio(  # pyright: ignore[reportUnusedFunction]
        user_id: Annotated[
            str,
            Form(description='User identifier owning the portfolio.'),
        ],
        files: Annotated[
            list[UploadFile],
            File(description='Image files to add to the portfolio.'),
        ],
        tags: Annotated[
            str | None,
            Form(description='Optional comma-separated tags applied to all files.'),
        ] = None,
    ) -> dict[str, list[str]]:
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='At least one file is required.',
            )
        svc = _require_vector_service()
        records = await _validate_and_build_records(
            files, user_id, _parse_tags(tags), config
        )
        try:
            ids = svc.save_portfolio_items(user_id=user_id, items=records)
        except RuntimeError as e:
            config.logger.exception('Failed to save portfolio items for user_id=%s', user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to save portfolio: {e!s}',
            ) from e
        return {'ids': ids}

    @router.get(
        '/history/{user_id}',
        summary='Get user portfolio and critique history',
        description=(
            'Returns a list of stored items (critiques and portfolio items) '
            'for the user, newest first. Optional type filter: critique or portfolio_item.'
        ),
    )
    async def get_history(  # pyright: ignore[reportUnusedFunction]
        user_id: str,
        limit: Annotated[
            int,
            Query(description='Max number of items to return', ge=1, le=500),
        ] = 100,
        type_filter: Annotated[
            str | None,
            Query(description='Filter by type: critique or portfolio_item'),
        ] = None,
    ) -> list[dict]:
        svc = _require_vector_service()
        return _fetch_user_history(svc, user_id, limit, type_filter, config)

    @router.get(
        '/item/{item_id}',
        summary='Get a single portfolio or critique item by ID',
        description='Returns full details (payload) for one stored item.',
    )
    async def get_item(item_id: str) -> dict:  # pyright: ignore[reportUnusedFunction]
        svc = _require_vector_service()
        return _get_item_or_raise(svc, item_id)

    return router
