"""Google Gemini AI configuration."""

import logging

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class GeminiConfig(BaseSettings):
    """Configuration for Google Gemini AI service."""

    model_config = ConfigDict(frozen=True)

    api_key: str = Field(
        ..., description='Google Gemini API Key', json_schema_extra={'env': 'GEMINI_API_KEY'}
    )
    model_name: str = Field(default='gemini-2.5-pro', description='Gemini model identifier')
    max_tokens: int = Field(default=2048, description='Maximum tokens in response')
    temperature: float = Field(
        default=0.7, ge=0.0, le=1.0, description='Temperature for creativity (0.0-1.0)'
    )
    timeout_seconds: int = Field(default=30, description='Request timeout in seconds')

    def setup(self, logger: logging.Logger) -> None:
        """
        Setup Gemini configuration with logger.

        Args:
            logger: Logger instance for logging setup info
        """
        logger.info('Gemini initialized with model: %s', self.model_name)
        logger.debug('Max tokens: %s, Temperature: %s', self.max_tokens, self.temperature)
