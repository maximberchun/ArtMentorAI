"""Server configuration."""

import logging

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class ServerConfig(BaseSettings):
    """Server configuration for FastAPI."""

    model_config = ConfigDict(frozen=True)

    host: str = Field(default='127.0.0.1', description='Server host address')
    port: int = Field(default=8000, description='Server port number')
    reload: bool = Field(
        default=False, description='Auto-reload on code changes (development only)'
    )

    def setup(self, logger: logging.Logger) -> None:
        """
        Setup server configuration with logger.

        Args:
            logger: Logger instance for logging setup info
        """
        logger.info('Server configured: %s:%s', self.host, self.port)
        if self.reload:
            logger.warning('Auto-reload enabled (development mode)')
