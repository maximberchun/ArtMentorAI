"""Application configuration container for ArtMentor AI."""

import logging
from typing import Protocol, runtime_checkable

from pydantic import ConfigDict, Field, PrivateAttr
from pydantic_settings import BaseSettings

from .gemini_config import GeminiConfig
from .server_config import ServerConfig
from .ssl_config import SSLConfig
from .upload_config import UploadConfig


@runtime_checkable
class _SetupProtocol(Protocol):
    """Protocol for configurations that need logger setup."""

    def setup(self, logger: logging.Logger) -> None: ...


class AppConfig(BaseSettings):
    """
    Configuration container for ArtMentor AI.

    This is the main configuration class that aggregates all sub-configurations.
    It follows the Protocol pattern for clean logger propagation.
    All configurations are frozen (immutable) to prevent accidental modifications.
    """

    model_config = ConfigDict(
        frozen=True,
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
        env_nested_delimiter='__',
    )

    # ============== Application Metadata ==============
    app_name: str = Field(default='ArtMentor AI', description='Application name')
    app_version: str = Field(default='0.1.0', description='Application version')
    debug: bool = Field(default=False, description='Debug mode enabled')
    environment: str = Field(
        default='development', description='Environment: development, staging, production'
    )

    # ============== CORS Settings ==============
    allowed_origins: list[str] = Field(
        default=['http://localhost:3000', 'http://localhost:8000'],
        description='CORS allowed origins',
    )

    # ============== Sub-configurations ==============
    server: ServerConfig = Field(default_factory=ServerConfig, description='Server configuration')
    ssl: SSLConfig = Field(default_factory=SSLConfig, description='SSL/TLS configuration')
    gemini: GeminiConfig = Field(..., description='Google Gemini configuration')
    upload: UploadConfig = Field(
        default_factory=UploadConfig, description='File upload configuration'
    )

    # ============== Private Logger ==============
    _logger: logging.Logger | None = PrivateAttr(default=None)

    def set_logger(self, logger: logging.Logger) -> None:
        """
        Assigns the externally created logger instance.

        This method propagates the logger to all sub-configurations
        that implement the _SetupProtocol interface.

        Args:
            logger: The logger instance to use throughout the application

        Raises:
            RuntimeError: If logger is None
        """
        if logger is None:
            msg = 'Logger instance cannot be None'
            raise RuntimeError(msg)

        self._logger = logger

        # Log application startup info
        logger.info('%s v%s initializing...', self.app_name, self.app_version)
        logger.info('Environment: %s', self.environment)
        logger.info('Debug mode: %s', self.debug)

        # Propagate logger to sub-configurations with setup() method
        for attr_name, attr_value in self.__dict__.items():
            if isinstance(attr_value, _SetupProtocol):
                logger.debug('Setting up sub-config: %s', attr_name)
                attr_value.setup(logger)

    @property
    def logger(self) -> logging.Logger:
        """
        Returns the logger instance.

        Must be initialized first via set_logger().

        Returns:
            logging.Logger: The configured logger instance

        Raises:
            RuntimeError: If logger not initialized
        """
        if self._logger is None:
            msg = 'Logger not initialized: call config.set_logger(...) first'
            raise RuntimeError(msg)
        return self._logger
