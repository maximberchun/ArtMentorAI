"""Shared validation helpers for image uploads across analysis and portfolio endpoints."""

from pathlib import Path

from fastapi import HTTPException, status

from ..config import AppConfig

MIME_ALIASES: dict[str, str] = {
    'image/jpg': 'image/jpeg',
    'image/jpe': 'image/jpeg',
    'image/tif': 'image/tiff',
}


def normalise_mime_type(mime: str) -> str:
    """Canonicalise non-standard MIME aliases to their registered IANA values.

    Args:
        mime: Raw MIME type string reported by the client.

    Returns:
        The canonical MIME type string (lowercased, alias-resolved).
    """
    return MIME_ALIASES.get(mime.lower(), mime.lower())


def validate_image_content_type(content_type: str | None) -> str:
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
    mime = normalise_mime_type(content_type or '')
    if not mime.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail='Unsupported media type. Only images are allowed.',
        )
    return mime


def validate_image_file(
    filename: str,
    content_type: str | None,
    config: AppConfig,
) -> tuple[str, str]:
    """Validate that file is a valid image (extension and MIME in allowlist).

    Args:
        filename: Name of the uploaded file
        content_type: MIME type of the file
        config: Application configuration (upload allowlists)

    Returns:
        tuple: (file_extension, mime_type)

    Raises:
        HTTPException 400: If extension or MIME type is not allowed.
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


def validate_file_size(
    content: bytes,
    max_file_size_mb: int,
) -> None:
    """Validate that file size is within limits and not empty.

    Args:
        content: File content bytes
        max_file_size_mb: Maximum allowed file size in MB

    Raises:
        HTTPException 413: If file is too large.
        HTTPException 400: If file is empty.
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
