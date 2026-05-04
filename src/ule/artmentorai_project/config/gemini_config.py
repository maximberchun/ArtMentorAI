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
    model_name: str = Field(
        default='gemini-2.5-flash',
        description='Gemini model identifier',
        json_schema_extra={'env': 'GEMINI_MODEL_NAME'},
    )
    model_fallbacks: str = Field(
        default='',
        description=(
            'Comma-separated extra Gemini model ids to try in order when the primary '
            'hits overload HTTP errors (503 / 429), or when the agent run times out'
        ),
        json_schema_extra={'env': 'GEMINI_MODEL_FALLBACKS'},
    )
    max_tokens: int = Field(default=2048, description='Maximum tokens in response')
    temperature: float = Field(
        default=0.7, ge=0.0, le=1.0, description='Temperature for creativity (0.0-1.0)'
    )
    timeout_seconds: int = Field(
        default=120,
        ge=15,
        le=600,
        description=(
            'Max seconds for one Gemini agent run (multimodal + tools); '
            'also used by asyncio client-side wait'
        ),
        json_schema_extra={'env': 'GEMINI_TIMEOUT_SECONDS'},
    )

    def model_try_chain(self) -> tuple[str, ...]:
        """Primary model first, then comma-separated fallbacks (deduplicated, trimmed)."""
        names: list[str] = [self.model_name]
        for part in self.model_fallbacks.split(','):
            candidate = part.strip()
            if candidate and candidate not in names:
                names.append(candidate)
        return tuple(names)

    def setup(self, logger: logging.Logger) -> None:
        """
        Setup Gemini configuration with logger.

        Args:
            logger: Logger instance for logging setup info
        """
        chain = self.model_try_chain()
        if len(chain) > 1:
            logger.info('Gemini model try order: %s', ' -> '.join(chain))
        else:
            logger.info('Gemini initialized with model: %s', self.model_name)
        logger.debug('Max tokens: %s, Temperature: %s', self.max_tokens, self.temperature)
