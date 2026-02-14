"""Endpoints for artwork analysis."""

from pathlib import Path
from typing import Annotated

from config import AppConfig
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from models import AnalysisResponse
from services import AgentService


def get_agent_service(config: AppConfig) -> AgentService:
    """Dependency injection for AgentService."""
    return AgentService(config)


def _validate_image_file(
    filename: str, content_type: str | None, config: AppConfig
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
            status_code=status.HTTP_400_BAD_REQUEST, detail=f'Extension not allowed. Use: {allowed}'
        )

    if actual_mime not in config.upload.allowed_mime_types:
        allowed = ', '.join(config.upload.allowed_mime_types)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f'MIME type not allowed. Use: {allowed}'
        )

    return file_extension, actual_mime


def _validate_file_size(content_length: int, config: AppConfig) -> None:
    """
    Validate that file size is within limits.

    Args:
        content_length: Size of the file in bytes
        config: Application configuration

    Raises:
        HTTPException: If file is too large or empty
    """
    max_size = config.upload.max_file_size_mb * 1024 * 1024
    if content_length > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f'File too large (max {config.upload.max_file_size_mb}MB)',
        )

    if content_length == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='File is empty')


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

    @router.post(
        '/critique',
        summary='Analyze an artwork',
        description='Send an image for structured feedback with score and recommendations',
    )
    async def critique_artwork(file: Annotated[UploadFile, File()]) -> AnalysisResponse:
        """
        Main endpoint for artwork analysis.

        Args:
            file: Image file to analyze

        Returns:
            AnalysisResponse: JSON with summary, score, technical_errors and advice

        Raises:
            HTTPException: If validation or processing fails
        """
        agent_service = AgentService(config)

        try:
            # Validate file
            _extension, mime_type = _validate_image_file(
                filename=file.filename or 'unknown', content_type=file.content_type, config=config
            )

            # Read content
            content = await file.read()

            # Validate size
            _validate_file_size(len(content), config)

            config.logger.info('Analyzing image: %s', file.filename)

            # Analyze with agent
            return await agent_service.analyze_image(image_bytes=content, mime_type=mime_type)

        except HTTPException:
            raise
        except Exception as e:
            config.logger.exception('Error processing image')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error analyzing image: {e!s}',
            ) from e

    @router.get(
        '/health', summary='Health check', description='Check if the analysis service is available'
    )
    async def health_check() -> dict:
        """Health check for analysis endpoint."""
        return {'status': 'healthy', 'service': 'ArtMentor AI - Analysis'}

    return router
