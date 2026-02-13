"""
Main package of the API project.

It provides the full structure for building a maintainable API, including:
- `config`: Application configuration, settings, and environment variables.
- `core`: Fundamental infrastructure, configuration, and shared utilities.
- `endpoints`: Route handlers and API controllers exposing functionality.
- `exceptions`: Custom exceptions and error handling.
- `models`: Data models, organized into `requests` and `responses`.
- `services`: Business logic and application workflows.
- `utils`: General-purpose helper functions and utilities.

This package serves as a starting point for building a scalable and
well-organized API, separating infrastructure, business logic, data
representation, and request handling into clear, maintainable layers.
"""
from .__version__ import __version__

__all__ = [
    '__version__',
]
