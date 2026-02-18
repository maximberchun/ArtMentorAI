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
from ..models import AnalysisResponse
from ..services import AgentService
from ..services.vector_service import ArtCritique, VectorService


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


def create_analysis_router(config: AppConfig) -> APIRouter:
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
            400: {'description': 'Invalid file'},
            413: {'description': 'File too large'},
            500: {'description': 'Server error'},
        },
    )

    # Initialize services
    agent_service = AgentService(config)
    vector_service = get_vector_service(config)

    @router.post(
        '/critique',
        summary='Analyze an artwork',
        description="""Send an image and optional comments for structured feedback with score
        and recommendations""",
    )
    async def critique_artwork(
        file: Annotated[UploadFile | None, File()] = None,
        user_comments: Annotated[str | None, Form()] = None,
    ) -> AnalysisResponse:
        """
        Main endpoint for artwork analysis with multimodal input support.

        Accepts both image file and optional user comments/questions.
        Processes artwork image through Gemini AI and stores the critique
        in vector database for long-term memory (RAG).

        Database failures are gracefully handled - the API returns the
        analysis even if vector DB is temporarily unavailable.

        Args:
            file: Image file to analyze (required)
            user_comments: Optional student comments about their work

        Returns:
            AnalysisResponse: JSON with summary, score, technical_errors, and advice

        Raises:
            HTTPException: If validation or processing fails
        """
        try:
            # Validate file
            _extension, mime_type = _validate_image_file(
                filename=file.filename or 'unknown',
                content_type=file.content_type,
                config=config,
            )

            # Read content
            content = await file.read()

            # Validate size and check if not empty
            _validate_file_size(content, config.upload.max_file_size_mb)

            # Log the request with context
            if user_comments:
                config.logger.info(
                    'Analyzing image: %s (with user comments)',
                    file.filename,
                )
            else:
                config.logger.info('Analyzing image: %s', file.filename)

            # Analyze with Gemini AI agent (pass user comments if provided)
            result = await agent_service.analyze_image(
                image_bytes=content,
                mime_type=mime_type,
                user_text=user_comments,
            )

            # ============== RAG: Store critique in vector database ==============
            # This is wrapped in try/except so the API doesn't fail if DB is down
            try:
                config.logger.debug('Attempting to store critique in vector database')

                # Convert analysis result to ArtCritique for vector storage
                if isinstance(result, dict):
                    result = AnalysisResponse(**result)

                critique = ArtCritique.from_analysis_response(result)
                # Save to Qdrant with filename as identifier
                filename = file.filename or 'unknown'
                vector_service.save_critique(critique, filename)

                config.logger.info(
                    'Critique stored in vector database: %s',
                    filename,
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
                return result

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
        is_healthy = vector_service.health_check()
        status_text = 'healthy' if is_healthy else 'unavailable'

        return {
            'status': status_text,
            'service': 'ArtMentor AI - Vector Database',
            'database': 'Qdrant',
        }

    return router
