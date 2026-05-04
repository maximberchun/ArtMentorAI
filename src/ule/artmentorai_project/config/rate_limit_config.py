"""Rate limit strings for SlowAPI (e.g. ``20/minute``)."""

import logging

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class RateLimitConfig(BaseSettings):
    """Per-route rate limits; override via env ``RATE_LIMITS__CRITIQUE`` etc."""

    model_config = ConfigDict(frozen=True)

    critique: str = Field(default='20/minute', description='Limit for POST /analysis/critique')
    chat: str = Field(default='40/minute', description='Limit for POST /analysis/chat')
    portfolio_upload: str = Field(
        default='25/minute',
        description='Limit for POST /portfolio/upload',
    )

    def setup(self, logger: logging.Logger) -> None:
        """Log configured limits at startup."""
        logger.info(
            'Rate limits: critique=%s chat=%s portfolio_upload=%s',
            self.critique,
            self.chat,
            self.portfolio_upload,
        )
