"""
The `utils` package provides general-purpose utility functions and helpers.

This package typically includes:
- Common functions or classes used across different modules.
- Helpers for string manipulation, date/time handling, or file operations.
- Generic utilities that do not belong to a specific layer (e.g., `core`, `services`, `models`).

Files placed here should contain reusable code that simplifies development,
avoiding duplication, while remaining independent from business logic or
framework-specific details.
"""

from .ssl_certificates import configure_ssl
from .upload_validation import (
    validate_file_size,
    validate_image_bytes_integrity,
    validate_image_content_type,
    validate_image_file,
)

__all__ = [
    'configure_ssl',
    'validate_file_size',
    'validate_image_bytes_integrity',
    'validate_image_content_type',
    'validate_image_file',
]
