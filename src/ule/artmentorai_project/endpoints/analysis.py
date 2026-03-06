"""Endpoints for artwork analysis with long-term memory (RAG).

This module provides REST endpoints for:
- Artwork critique generation using Gemini AI
- Automatic storage in vector database for future reference
- Multimodal input support (image + optional user comments)
- Error handling that doesn't break the API if vector DB is down
"""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from ..config import AppConfig
from ..models import AnalysisResponse, UserProfile
from ..services import AgentService, ProfileService
from ..services.vector_service import ArtCritique, VectorService

_MIME_ALIASES: dict[str, str] = {
    'image/jpg': 'image/jpeg',
    'image/jpe': 'image/jpeg',
    'image/tif': 'image/tiff',
}


def _normalise_mime_type(mime: str) -> str:
    """Canonicalise non-standard MIME aliases to their registered IANA values.

    Args:
        mime: Raw MIME type string reported by the client.

    Returns:
        The canonical MIME type string (lowercased, alias-resolved).
    """
    return _MIME_ALIASES.get(mime.lower(), mime.lower())


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
    return VectorService(
        host='localhost',
        port=6333,
        logger=config.logger,
    )


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


def _validate_image_content_type(content_type: str | None) -> str:
    """Enforce that the uploaded file is an image.

    Uses a prefix check on the MIME type so that any ``image/*`` variant
    (jpeg, png, webp, gif, …) is accepted without maintaining an allowlist,
    while still rejecting everything else.

    Args:
        content_type: The ``content_type`` reported by the browser / client.

    Returns:
        The validated, normalised MIME type string.

    Raises:
        HTTPException 415: If the content type is absent or not an image.
    """
    mime = _normalise_mime_type(content_type or '')
    if not mime.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail='Unsupported media type. Only images are allowed.',
        )
    return mime


def _validate_image_file(
    filename: str,
    content_type: str | None,
    config: AppConfig,
) -> tuple[str, str]:
    """
    Validate that file is a valid image.

    Args:
        filename: Name of the uploaded file
        content_type: MIME type of the file
        config: Application configuration

    Returns:
        tuple: (file_extension, mime_type)

    Raises:
        HTTPException: If file is not valid
    """
    file_extension = Path(filename).suffix.lower()
    actual_mime = content_type or 'image/jpeg'

    if file_extension not in config.upload.allowed_extensions:
        allowed = ', '.join(config.upload.allowed_extensions)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Extension not allowed. Use: {allowed}',
        )

    if actual_mime not in config.upload.allowed_mime_types:
        allowed = ', '.join(config.upload.allowed_mime_types)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'MIME type not allowed. Use: {allowed}',
        )

    return file_extension, actual_mime


def _validate_file_size(
    content: bytes,
    max_file_size_mb: int,
) -> None:
    """
    Validate that file size is within limits.

    Args:
        content: File content bytes
        max_file_size_mb: Maximum allowed file size in MB

    Raises:
        HTTPException: If file is too large or empty
    """
    max_size = max_file_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f'File too large (max {max_file_size_mb}MB)',
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='File is empty',
        )


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
    try:
        vector_service: VectorService | None = get_vector_service(config)
    except RuntimeError as init_error:
        config.logger.warning(
            'VectorService unavailable at startup: %s. '
            'Continuing without long-term memory until Qdrant is restored.',
            str(init_error),
        )
        vector_service = None

    @router.post(
        '/critique',
        summary='Analyze an artwork',
        description="""Send an image and optional comments for structured feedback with score
        and recommendations""",
    )
    async def critique_artwork(
        user_id: Annotated[
            str,
            Form(description='Mandatory user identifier for the RAG system.'),
        ],
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

        The ``user_id`` is mandatory so that critiques can be associated
        with a specific artist in the vector database.

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
            user_id:    Mandatory user identifier for the RAG pipeline.

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

            if file is not None:
                mime_type = _validate_image_content_type(file.content_type)

                image_bytes = await file.read()

                _validate_file_size(image_bytes, config.upload.max_file_size_mb)

                _extension, mime_type = _validate_image_file(
                    filename=file.filename or 'unknown',
                    content_type=mime_type,
                    config=config,
                )

            # Log the request with context
            config.logger.info(
                'Analyzing input — file: %s | user_input: %s | user_id: %s',
                file.filename if file else 'none',
                'yes' if user_input else 'none',
                user_id,
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
                        user_id=user_id,
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
                            user_id,
                        )
                    else:
                        config.logger.debug(
                            'No past critiques found for user_id=%s — proceeding without memory',
                            user_id,
                        )
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as memory_error:
                    config.logger.warning(
                        'Memory retrieval failed for user_id=%s: %s. '
                        'Proceeding without history context.',
                        user_id,
                        str(memory_error),
                    )
            else:
                config.logger.debug(
                    'VectorService not available; proceeding without memory for user_id=%s',
                    user_id,
                )

            # Load optional user profile for personalised critique
            profile_context_str: str | None = None
            try:
                profile = profile_service.get_profile(user_id)
            except RuntimeError as e:
                config.logger.warning(
                    'Failed to load profile for user_id=%s: %s. Proceeding without profile.',
                    user_id,
                    str(e),
                )
            else:
                if profile is not None:
                    profile_context_str = _format_profile_for_prompt(profile)
                    config.logger.debug(
                        'Injecting profile context into prompt for user_id=%s',
                        user_id,
                    )

            # Analyze with Gemini AI agent
            result = await agent_service.analyze_image(
                image_bytes=image_bytes,
                mime_type=mime_type,
                user_input=user_input,
                past_critiques=past_critiques_str,
                profile_context=profile_context_str,
            )

            # ============== RAG: Store critique in vector database ==============
            # This is wrapped in try/except so the API doesn't fail if DB is down
            if vector_service is not None:
                try:
                    config.logger.debug('Attempting to store critique in vector database')

                    # Convert analysis result to ArtCritique for vector storage
                    if isinstance(result, dict):
                        result = AnalysisResponse(**result)

                    critique = ArtCritique.from_analysis_response(result)
                    # Save to Qdrant with filename as identifier
                    artwork_filename = (file.filename if file is not None else None) or 'unknown'
                    vector_service.save_critique(critique, artwork_filename, user_id=user_id)

                    config.logger.info(
                        'Critique stored in vector database: %s (user_id=%s)',
                        artwork_filename,
                        user_id,
                    )

                except (ConnectionError, TimeoutError, OSError) as vector_error:
                    # Log the error but don't fail the API
                    config.logger.warning(
                        'Failed to store critique in vector database: %s. '
                        'Continuing with analysis response.',
                        str(vector_error),
                    )
                    # Continue - the analysis is still returned to the user
            else:
                config.logger.debug(
                    'Skipping vector database storage because VectorService is unavailable '
                    '(user_id=%s)',
                    user_id,
                )

            # Always return the analysis even if vector DB operations failed.
            return result  # noqa: TRY300

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
