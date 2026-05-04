"""Shared validation helpers for image uploads across analysis and portfolio endpoints."""

from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, status
from PIL import Image, UnidentifiedImageError

from ..config import AppConfig

MIME_ALIASES: dict[str, str] = {
    'image/jpg': 'image/jpeg',
    'image/jpe': 'image/jpeg',
    'image/tif': 'image/tiff',
}

_MIN_BYTES_FOR_SNIFF = 12

_EXTENSION_EXPECTED_MIMES: dict[str, frozenset[str]] = {
    '.jpg': frozenset({'image/jpeg'}),
    '.jpeg': frozenset({'image/jpeg'}),
    '.png': frozenset({'image/png'}),
    '.gif': frozenset({'image/gif'}),
    '.webp': frozenset({'image/webp'}),
    '.bmp': frozenset({'image/bmp'}),
}


def normalise_mime_type(mime: str) -> str:
    """Canonicalise non-standard MIME aliases to their registered IANA values.

    Args:
        mime: Raw MIME type string reported by the client.

    Returns:
        The canonical MIME type string (lowercased, alias-resolved).
    """
    return MIME_ALIASES.get(mime.lower(), mime.lower())


def sniff_image_mime(content: bytes) -> str | None:  # noqa: PLR0911
    """Detect image format from magic bytes (not from client headers).

    Args:
        content: Raw file bytes.

    Returns:
        Canonical ``image/*`` MIME if recognised, else ``None``.
    """
    if len(content) < _MIN_BYTES_FOR_SNIFF:
        return None
    if content[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if content[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if content[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    if content[:2] == b'BM':
        return 'image/bmp'
    if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return 'image/webp'
    return None


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
    actual_mime = normalise_mime_type(content_type or 'image/jpeg')

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


def validate_image_bytes_integrity(content: bytes, filename: str, declared_mime: str) -> None:
    """Confirm bytes match declared image type (magic bytes + decodable image).

    Args:
        content: Full file body (already size-checked).
        filename: Original filename (extension cross-check).
        declared_mime: Normalised MIME from headers and allowlist.

    Raises:
        HTTPException 400: If bytes are not a valid image or disagree with extension/MIME.
    """
    sniffed = sniff_image_mime(content)
    declared = normalise_mime_type(declared_mime)
    if sniffed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid image file or unsupported image format.',
        )
    if sniffed != declared:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Image content does not match its declared type.',
        )
    suffix = Path(filename).suffix.lower()
    expected = _EXTENSION_EXPECTED_MIMES.get(suffix)
    if expected is None or sniffed not in expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Image content does not match the file extension.',
        )
    try:
        with Image.open(BytesIO(content)) as img:
            img.verify()
    except (OSError, SyntaxError, ValueError, TypeError, UnidentifiedImageError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Image file is corrupted or could not be decoded.',
        ) from None


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
