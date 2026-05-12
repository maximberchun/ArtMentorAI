"""Tests for upload sniffing, extension alignment, and decode checks."""

from __future__ import annotations

import logging
from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image

from ule.artmentorai_project.config import AppConfig
from ule.artmentorai_project.utils.upload_validation import (
    normalise_mime_type,
    sniff_image_mime,
    validate_image_bytes_integrity,
    validate_image_content_type,
    validate_image_file,
)


@pytest.fixture
def upload_app_config(monkeypatch: pytest.MonkeyPatch) -> AppConfig:
    monkeypatch.setenv('OPENROUTER__API_KEY', 'test-openrouter-api-key')
    monkeypatch.setenv('SUPABASE__URL', 'https://example.supabase.co')
    cfg = AppConfig()
    cfg.set_logger(logging.getLogger('tests.upload_validation'))
    return cfg


def _png_bytes() -> bytes:
    buf = BytesIO()
    Image.new('RGB', (2, 2), color=(10, 20, 30)).save(buf, format='PNG')
    return buf.getvalue()


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new('RGB', (2, 2), color=(40, 50, 60)).save(buf, format='JPEG')
    return buf.getvalue()


def test_normalise_mime_type_maps_common_aliases() -> None:
    assert normalise_mime_type('image/JPG') == 'image/jpeg'
    assert normalise_mime_type('image/png') == 'image/png'


@pytest.mark.parametrize(
    ('prefix', 'expected'),
    [
        (b'\xff\xd8\xff\xe0\x00\x10JFIF', 'image/jpeg'),
        (_png_bytes()[:32], 'image/png'),
        (b'GIF89a\x01\x00\x01\x00\x80\x00\x00', 'image/gif'),
        (b'BM\x36\x00\x00\x00\x00\x00\x00\x00', 'image/bmp'),
    ],
)
def test_sniff_image_mime_recognises_formats(prefix: bytes, expected: str) -> None:
    if expected == 'image/png':
        content = _png_bytes()
    elif expected == 'image/bmp':
        content = prefix + b'\x00' * 40
    else:
        content = prefix + b'\x00' * 24
    assert sniff_image_mime(content) == expected


def test_sniff_image_mime_webp() -> None:
    # Minimal RIFF....WEBP header (payload not a full VP8 chunk; sniff only checks prefix)
    content = b'RIFF' + (36).to_bytes(4, 'little') + b'WEBP' + b'VP8 ' + b'\x00' * 32
    assert sniff_image_mime(content) == 'image/webp'


def test_sniff_image_mime_rejects_short_or_unknown() -> None:
    assert sniff_image_mime(b'') is None
    assert sniff_image_mime(b'not an image!!!!') is None


def test_validate_image_bytes_integrity_accepts_matching_png(upload_app_config: AppConfig) -> None:
    content = _png_bytes()
    _, mime = validate_image_file('art.png', 'image/png', upload_app_config)
    validate_image_bytes_integrity(content, 'art.png', mime)


def test_validate_image_bytes_integrity_rejects_mime_mismatch() -> None:
    content = _png_bytes()
    with pytest.raises(HTTPException) as excinfo:
        validate_image_bytes_integrity(content, 'art.png', 'image/jpeg')
    assert excinfo.value.status_code == 400


def test_validate_image_bytes_integrity_rejects_extension_mismatch(
    upload_app_config: AppConfig,
) -> None:
    content = _png_bytes()
    _, mime = validate_image_file('disguised.jpg', 'image/png', upload_app_config)
    with pytest.raises(HTTPException) as excinfo:
        validate_image_bytes_integrity(content, 'disguised.jpg', mime)
    assert excinfo.value.status_code == 400


def test_validate_image_bytes_integrity_rejects_corrupt_payload(upload_app_config: AppConfig) -> None:
    corrupt = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20
    _, mime = validate_image_file('x.png', 'image/png', upload_app_config)
    with pytest.raises(HTTPException) as excinfo:
        validate_image_bytes_integrity(corrupt, 'x.png', mime)
    assert excinfo.value.status_code == 400


def test_validate_image_content_type_rejects_non_image_payload() -> None:
    with pytest.raises(HTTPException) as excinfo:
        validate_image_content_type('application/octet-stream')
    assert excinfo.value.status_code == 415


def test_validate_image_content_type_rejects_missing_type() -> None:
    with pytest.raises(HTTPException) as excinfo:
        validate_image_content_type(None)
    assert excinfo.value.status_code == 415


def test_validate_image_file_rejects_spoofed_vector_mime(upload_app_config: AppConfig) -> None:
    """Declared browser MIME must stay within the configured raster allowlist (blocks SVG/ZIP, etc.)."""
    with pytest.raises(HTTPException) as excinfo:
        validate_image_file('logo.png', 'image/svg+xml', upload_app_config)
    assert excinfo.value.status_code == 400


def test_validate_image_bytes_integrity_rejects_jpeg_disguised_as_png(
    upload_app_config: AppConfig,
) -> None:
    """Magic-byte sniffing must win over filename and Content-Type (polyglot bypass)."""
    jpeg = _jpeg_bytes()
    _, mime = validate_image_file('innocent.png', 'image/png', upload_app_config)
    with pytest.raises(HTTPException) as excinfo:
        validate_image_bytes_integrity(jpeg, 'innocent.png', mime)
    assert excinfo.value.status_code == 400
    assert 'declared' in (excinfo.value.detail or '').lower()
