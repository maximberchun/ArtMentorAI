"""OpenRouter LLM configuration (Pydantic AI)."""

import logging

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class OpenRouterConfig(BaseSettings):
    """Configuration for OpenRouter-backed models via Pydantic AI."""

    model_config = ConfigDict(frozen=True)

    api_key: str = Field(
        ...,
        description='OpenRouter API key',
        json_schema_extra={'env': 'OPENROUTER_API_KEY'},
    )
    model_name: str = Field(
        default='google/gemini-2.5-flash',
        description='OpenRouter model slug (vendor/model), without openrouter: prefix',
        json_schema_extra={'env': 'OPENROUTER_MODEL_NAME'},
    )
    model_fallbacks: str = Field(
        default='',
        description=(
            'Comma-separated extra OpenRouter model slugs to try when the primary '
            'hits overload HTTP errors (503 / 429), or when the agent run times out'
        ),
        json_schema_extra={'env': 'OPENROUTER_MODEL_FALLBACKS'},
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
            'Max seconds for one LLM agent run (multimodal + tools); '
            'also used by asyncio client-side wait'
        ),
        json_schema_extra={'env': 'OPENROUTER_TIMEOUT_SECONDS'},
    )
    app_title: str = Field(
        default='ArtMentor AI',
        description='OpenRouter app attribution title',
        json_schema_extra={'env': 'OPENROUTER_APP_TITLE'},
    )
    app_url: str = Field(
        default='https://artmentorai.vercel.app',
        description='OpenRouter app attribution URL',
        json_schema_extra={'env': 'OPENROUTER_APP_URL'},
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
        Setup OpenRouter configuration with logger.

        Args:
            logger: Logger instance for logging setup info
        """
        chain = self.model_try_chain()
        if len(chain) > 1:
            logger.info('OpenRouter model try order: %s', ' -> '.join(chain))
        else:
            logger.info('OpenRouter initialized with model: %s', self.model_name)
        logger.debug('Max tokens: %s, Temperature: %s', self.max_tokens, self.temperature)
