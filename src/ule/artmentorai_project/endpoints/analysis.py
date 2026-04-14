"""Endpoints for artwork analysis with long-term memory (RAG).

This module provides REST endpoints for:
- Artwork critique generation using Gemini AI
- Automatic storage in vector database for future reference
- Multimodal input support (image + optional user comments)
- Error handling that doesn't break the API if vector DB is down
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import AppConfig
from ..db.supabase_client import create_supabase_service_client
from ..exceptions import AIServiceError
from ..models import AnalysisResponse, AuthUser, UserProfile
from ..repositories import CritiqueRepository, ImageAssetRepository, VectorSyncJobRepository
from ..repositories.vector_sync_job_repository import ENTITY_CRITIQUE, OP_UPSERT
from ..services import AgentService, ProfileService, StorageService
from ..services.auth_service import AuthService
from ..services.vector_service import ArtCritique, VectorService
from ..utils.upload_validation import (
    validate_file_size,
    validate_image_content_type,
    validate_image_file,
)

_bearer = HTTPBearer(auto_error=True)


def _build_current_user_dependency(config: AppConfig) -> Callable[..., Awaitable[AuthUser]]:
    auth = AuthService(config)

    async def _current_user(
        creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    ) -> AuthUser:
        return await auth.verify_access_token(creds.credentials)

    return _current_user


def get_agent_service(config: AppConfig) -> AgentService:
    """Dependency injection for AgentService."""
    return AgentService(config)


def get_vector_service(config: AppConfig) -> VectorService:
    """Dependency injection for VectorService.

    Creates or reuses VectorService instance with proper logger.

    Args:
        config: Application configuration

    Returns:
        VectorService: Initialized vector service instance
    """
    return VectorService(config=config, logger=config.logger)


def get_storage_service(config: AppConfig) -> StorageService:
    """Dependency injection for StorageService."""
    return StorageService(config)


def _format_profile_for_prompt(profile: UserProfile) -> str:
    """Create a compact textual description of the user profile for the agent."""
    parts: list[str] = []

    if profile.goals:
        parts.append('Goals: ' + '; '.join(profile.goals))
    if profile.preferred_styles:
        parts.append('Preferred styles: ' + '; '.join(profile.preferred_styles))
    if profile.disliked_styles:
        parts.append('Disliked styles: ' + '; '.join(profile.disliked_styles))
    if profile.favorite_artists:
        parts.append('Favorite artists: ' + '; '.join(profile.favorite_artists))
    if profile.experience_level:
        parts.append('Experience level: ' + profile.experience_level)

    return ' | '.join(parts)


def _require_at_least_one_input(
    file: UploadFile | None,
    user_input: str | None,
) -> None:
    """Raise HTTP 422 if neither a file nor a text comment was provided.

    Extracted into a standalone function so the ``raise`` is not sitting
    directly inside a ``try`` block (Ruff TRY301).

    Args:
        file:       The uploaded file, or ``None`` if omitted.
        user_input: The user's text comment, or ``None`` / blank if omitted.

    Raises:
        HTTPException 422: If both inputs are absent.
    """
    if file is None and not (user_input and user_input.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Provide at least an image, a text comment, or both.',
        )


def create_analysis_router(config: AppConfig) -> APIRouter:  # noqa: C901, PLR0915
    """
    Create analysis router with configuration.

    Args:
        config: Application configuration

    Returns:
        APIRouter: Configured router for analysis endpoints
    """
    router = APIRouter(
        prefix='/analysis',
        tags=['Analysis'],
        responses={
            400: {'description': 'Invalid file (extension, MIME type, or empty file)'},
            413: {'description': 'File too large'},
            415: {'description': 'Unsupported media type (only images allowed)'},
            422: {'description': 'Validation error (missing image and text)'},
            500: {'description': 'Server error'},
        },
    )

    # Initialize services
    agent_service = AgentService(config)
    profile_service = ProfileService(logger=config.logger)
    current_user = _build_current_user_dependency(config)
    try:
        vector_service: VectorService | None = get_vector_service(config)
    except RuntimeError as init_error:
        config.logger.warning(
            'VectorService unavailable at startup: %s. '
            'Continuing without long-term memory until Qdrant is restored.',
            str(init_error),
        )
        vector_service = None
    try:
        storage_service: StorageService | None = get_storage_service(config)
    except RuntimeError as init_error:
        config.logger.warning(
            'StorageService unavailable at startup: %s. Continuing without image persistence.',
            str(init_error),
        )
        storage_service = None

    @router.post(
        '/critique',
        summary='Analyze an artwork',
        description="""Send an image and optional comments for structured feedback with score
        and recommendations""",
    )
    async def critique_artwork(  # noqa: C901, PLR0912, PLR0915
        user: Annotated[AuthUser, Depends(current_user)],
        file: Annotated[
            UploadFile | None, File(description='The artwork image to analyse.')
        ] = None,
        user_input: Annotated[
            str | None,
            Form(description='Optional user comments about their work.'),
        ] = None,
    ) -> AnalysisResponse:
        """
        Main endpoint for artwork analysis with multimodal input support.

        The endpoint accepts:

        - **Image-only** requests (file provided, no user_input).
        - **Text-only** requests (user_input provided, no file) — for
          analysis of written descriptions or questions.
        - **Image + text** requests (both provided) for fully contextualised
          critiques.

        The authenticated user's id is derived from the Supabase access token
        so that critiques can be associated with a specific artist in the vector database.

        Validation order (fail-fast):

        1. At least one of ``file`` or ``user_input`` must be provided → HTTP 422.
        2. If a file is present, ``content_type`` must start with ``"image/"`` → HTTP 415.
        3. File bytes must not exceed ``MAX_FILE_SIZE_MB`` from .env   → HTTP 413.
        4. Extension and MIME type must be in allowlist                → HTTP 400.
        5. File must not be empty                                      → HTTP 400.

        Database failures are gracefully handled — the API still returns the
        analysis even if the vector DB is temporarily unavailable or could
        not be initialised at startup.

        Args:
            file:       Optional image file to analyse.
            user_input: Optional user comments or description of the artwork.
            user:       Authenticated user identity (from Supabase access token).

        Returns:
            AnalysisResponse: JSON with summary, score, technical_errors, advice.

        Raises:
            HTTPException 415: Unsupported file type.
            HTTPException 413: File exceeds MAX_FILE_SIZE_MB limit (.env).
            HTTPException 400: Invalid extension / empty file.
            HTTPException 422: Neither image nor text was provided.
            HTTPException 500: Unexpected processing error.
        """
        # Ensure that at least image or text is provided.
        _require_at_least_one_input(file=file, user_input=user_input)

        try:
            # File validation
            image_bytes: bytes | None = None
            mime_type: str | None = None
            image_path: str | None = None

            if file is not None:
                mime_type = validate_image_content_type(file.content_type)

                image_bytes = await file.read()

                validate_file_size(image_bytes, config.upload.max_file_size_mb)

                _extension, mime_type = validate_image_file(
                    filename=file.filename or 'unknown',
                    content_type=mime_type,
                    config=config,
                )
                if storage_service is not None and image_bytes is not None:
                    try:
                        image_path = storage_service.upload_image(
                            user_id=user.user_id,
                            image_bytes=image_bytes,
                            filename=file.filename or 'unknown',
                            mime_type=mime_type,
                        )
                    except RuntimeError as storage_error:
                        config.logger.warning(
                            'Image upload failed for user_id=%s: %s. '
                            'Continuing without persisted image reference.',
                            user.user_id,
                            str(storage_error),
                        )

            # Log the request with context
            config.logger.info(
                'Analyzing input — file: %s | user_input: %s | user_id: %s',
                file.filename if file else 'none',
                'yes' if user_input else 'none',
                user.user_id,
            )

            past_critiques_str: str | None = None
            if vector_service is not None:
                try:
                    # Use the user's own comment as the semantic query when
                    # available; fall back to a generic drawing-error query so
                    # we always attempt to surface relevant history.
                    memory_query = (
                        user_input.strip()
                        if user_input and user_input.strip()
                        else 'technical drawing errors anatomy perspective'
                    )
                    past_records = vector_service.search_similar_critiques(
                        query_text=memory_query,
                        user_id=user.user_id,
                    )
                    if past_records:
                        past_critiques_str = (
                            ''.join(
                                f'- Summary: {r["summary"]} | Advice: {r["advice"]}'
                                for r in past_records
                                if r.get('summary') or r.get('advice')
                            )
                            or None
                        )  # collapse to None if every record had empty fields
                        config.logger.debug(
                            'Injecting %d past critique(s) into prompt for user_id=%s',
                            len(past_records),
                            user.user_id,
                        )
                    else:
                        config.logger.debug(
                            'No past critiques found for user_id=%s — proceeding without memory',
                            user.user_id,
                        )
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as memory_error:
                    config.logger.warning(
                        'Memory retrieval failed for user_id=%s: %s. '
                        'Proceeding without history context.',
                        user.user_id,
                        str(memory_error),
                    )
            else:
                config.logger.debug(
                    'VectorService not available; proceeding without memory for user_id=%s',
                    user.user_id,
                )

            # Load optional user profile for personalised critique
            profile_context_str: str | None = None
            try:
                profile = profile_service.get_profile(user.user_id)
            except RuntimeError as e:
                config.logger.warning(
                    'Failed to load profile for user_id=%s: %s. Proceeding without profile.',
                    user.user_id,
                    str(e),
                )
            else:
                if profile is not None:
                    profile_context_str = _format_profile_for_prompt(profile)
                    config.logger.debug(
                        'Injecting profile context into prompt for user_id=%s',
                        user.user_id,
                    )

            # Analyze with Gemini AI agent
            result = await agent_service.analyze_image(
                image_bytes=image_bytes,
                mime_type=mime_type,
                user_input=user_input,
                past_critiques=past_critiques_str,
                profile_context=profile_context_str,
            )

            # Persist critique - Postgres + async Qdrant sync
            analysis_result = AnalysisResponse(**result) if isinstance(result, dict) else result

            synced_via_pg = False
            try:
                sb = create_supabase_service_client(config)
                image_asset_id = None
                if image_path is not None:
                    img_repo = ImageAssetRepository(sb, config.logger)
                    asset = img_repo.create(
                        user_id=user.user_id,
                        storage_bucket=config.supabase.storage_bucket,
                        storage_object_path=image_path,
                        mime_type=mime_type,
                        original_filename=file.filename if file is not None else None,
                        byte_size=len(image_bytes) if image_bytes else None,
                    )
                    image_asset_id = asset.id
                cr_repo = CritiqueRepository(sb, config.logger)
                artwork_filename = (file.filename if file is not None else None) or 'unknown'
                row = cr_repo.create(
                    user_id=user.user_id,
                    summary=analysis_result.summary,
                    score=analysis_result.score,
                    technical_errors=analysis_result.technical_errors,
                    constructive_advice=analysis_result.constructive_advice,
                    tags=[],
                    goals_snapshot=profile_context_str,
                    image_asset_id=image_asset_id,
                    artwork_filename=artwork_filename,
                )
                VectorSyncJobRepository(sb, config.logger).enqueue(
                    ENTITY_CRITIQUE,
                    row.id,
                    OP_UPSERT,
                )
                synced_via_pg = True
                config.logger.info(
                    'Critique persisted to Postgres and queued for Qdrant: id=%s user_id=%s',
                    row.id,
                    user.user_id,
                )
            except RuntimeError as persist_error:
                config.logger.warning(
                    'Postgres critique persistence / enqueue failed: %s',
                    str(persist_error),
                )

            if not synced_via_pg and vector_service is not None:
                try:
                    config.logger.debug('Fallback: store critique directly in Qdrant')
                    artwork_filename = (file.filename if file is not None else None) or 'unknown'
                    critique = ArtCritique.from_analysis_response(
                        analysis_result,
                        goals_snapshot=profile_context_str,
                    )
                    vector_service.save_critique(
                        critique,
                        artwork_filename,
                        user_id=user.user_id,
                        image_path=image_path,
                    )
                    config.logger.info(
                        'Critique stored in vector database (fallback): %s (user_id=%s)',
                        artwork_filename,
                        user.user_id,
                    )
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as vector_error:
                    config.logger.warning(
                        'Failed to store critique in vector database: %s. '
                        'Continuing with analysis response.',
                        str(vector_error),
                    )
                    if storage_service is not None and image_path is not None:
                        storage_service.delete_file(image_path)
            elif not synced_via_pg:
                config.logger.debug(
                    'Skipping vector storage (no Postgres, no VectorService) user_id=%s',
                    user.user_id,
                )

            # Always return the analysis even if vector DB operations failed
            return analysis_result  # noqa: TRY300

        except AIServiceError as e:
            config.logger.warning('AI service error: %s (code=%s)', e.message, e.error_code)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    'error': e.error_code,
                    'message': e.message,
                    'retry_after': e.retry_after,
                },
            ) from e
        except HTTPException:
            raise
        except Exception as e:
            config.logger.exception('Error processing image')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error analyzing image: {e!s}',
            ) from e

    @router.get(
        '/health',
        summary='Health check',
        description='Check if the analysis service is available',
    )
    async def health_check() -> dict[str, str]:
        """Health check for analysis endpoint."""
        return {
            'status': 'healthy',
            'service': 'ArtMentor AI - Analysis',
        }

    @router.get(
        '/vector-db-health',
        summary='Vector Database health check',
        description='Check if the vector database is accessible',
    )
    async def vector_db_health() -> dict[str, str]:
        """Health check for vector database connection."""
        is_healthy = vector_service.health_check() if vector_service is not None else False
        status_text = 'healthy' if is_healthy else 'unavailable'

        return {
            'status': status_text,
            'service': 'ArtMentor AI - Vector Database',
            'database': 'Qdrant',
        }

    return router
