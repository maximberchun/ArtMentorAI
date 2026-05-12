"""Application configuration container for ArtMentor AI."""

import logging
from typing import Literal, Protocol, Self, runtime_checkable

from pydantic import ConfigDict, Field, PrivateAttr, model_validator
from pydantic_settings import BaseSettings

from .openrouter_config import OpenRouterConfig
from .rate_limit_config import RateLimitConfig
from .server_config import ServerConfig
from .ssl_config import SSLConfig
from .supabase_config import SupabaseConfig
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
        default=[
            'http://localhost:3000',
            'http://localhost:5173',
            'http://127.0.0.1:5173',
            'http://localhost:8000',
            'http://127.0.0.1:8000',
        ],
        description='CORS allowed origins',
    )

    cors_allow_methods: list[str] = Field(
        default=['GET', 'POST', 'PUT', 'OPTIONS', 'HEAD'],
        description='CORS allowed HTTP methods',
    )

    cors_allow_headers: list[str] = Field(
        default=[
            'Accept',
            'Authorization',
            'Content-Type',
            'Origin',
            'X-Requested-With',
        ],
        description='CORS allowed request headers',
    )

    # ============== Sub-configurations ==============
    server: ServerConfig = Field(default_factory=ServerConfig, description='Server configuration')
    ssl: SSLConfig = Field(default_factory=SSLConfig, description='SSL/TLS configuration')
    openrouter: OpenRouterConfig = Field(..., description='OpenRouter LLM configuration')
    supabase: SupabaseConfig = Field(..., description='Supabase configuration (Auth/JWT)')
    upload: UploadConfig = Field(
        default_factory=UploadConfig, description='File upload configuration'
    )
    rate_limits: RateLimitConfig = Field(
        default_factory=RateLimitConfig,
        description='SlowAPI rate limit strings for expensive routes',
    )
    qdrant_host: str = Field(default='localhost', description='Qdrant host')
    qdrant_port: int = Field(default=6333, description='Qdrant HTTP port')
    qdrant_url: str | None = Field(
        default=None,
        description='Optional full Qdrant URL (preferred for managed TLS endpoints)',
    )
    qdrant_api_key: str | None = Field(
        default=None,
        description='Optional Qdrant API key',
    )
    qdrant_collection_name: str = Field(
        default='art_portfolio',
        description='Qdrant collection name for vector points',
    )
    qdrant_timeout_seconds: float = Field(
        default=10.0,
        description='Qdrant request timeout in seconds',
    )
    embedding_model_name: str = Field(
        default='BAAI/bge-small-en-v1.5',
        description='Embedding model identifier',
    )
    embedding_size: int = Field(
        default=384,
        description='Embedding dimensionality',
    )
    embedding_cache_folder: str = Field(
        default='./embeddings_cache',
        description='Local folder for embedding model cache',
    )
    web_search_enabled: bool = Field(
        default=False,
        description='Enable web-search tool for the AI agent',
    )
    web_search_provider: Literal['serper'] = Field(
        default='serper',
        description='Configured web-search provider identifier',
    )
    web_search_api_key: str | None = Field(
        default=None,
        description='API key for the configured web-search provider',
    )
    web_search_timeout_seconds: float = Field(
        default=8.0,
        ge=1.0,
        le=30.0,
        description='Timeout for outbound web-search requests',
    )
    web_search_max_calls_per_request: int = Field(
        default=2,
        ge=1,
        le=5,
        description='Maximum number of tool calls the model can make per critique request',
    )
    web_search_max_results: int = Field(
        default=3,
        ge=1,
        le=10,
        description='Maximum number of search hits returned per tool call',
    )
    web_search_max_query_chars: int = Field(
        default=240,
        ge=32,
        le=500,
        description='Maximum length accepted for model-generated web-search queries',
    )

    # ============== Private Logger ==============
    _logger: logging.Logger | None = PrivateAttr(default=None)

    @model_validator(mode='after')
    def _validate_production_cors(self) -> Self:
        """Disallow wildcard or non-HTTPS browser origins in production."""
        if self.environment.lower() != 'production':
            return self
        for origin in self.allowed_origins:
            if origin == '*':
                msg = 'Wildcard CORS origin is not allowed when ENVIRONMENT=production'
                raise ValueError(msg)
            if not origin.startswith('https://'):
                msg = f'Production CORS origins must use HTTPS (got {origin!r})'
                raise ValueError(msg)
        return self

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
