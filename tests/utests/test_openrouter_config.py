"""Unit tests for OpenRouter configuration."""

from ule.artmentorai_project.config.openrouter_config import OpenRouterConfig


def test_model_try_chain_dedupes_and_orders() -> None:
    cfg = OpenRouterConfig(
        api_key='k',
        model_name='google/gemini-2.5-flash',
        model_fallbacks=' google/gemini-2.0-flash , google/gemini-2.5-flash ,openai/gpt-4o',
    )
    assert cfg.model_try_chain() == (
        'google/gemini-2.5-flash',
        'google/gemini-2.0-flash',
        'openai/gpt-4o',
    )


def test_model_try_chain_single_model() -> None:
    cfg = OpenRouterConfig(api_key='k', model_name='anthropic/claude-3.5-sonnet', model_fallbacks='')
    assert cfg.model_try_chain() == ('anthropic/claude-3.5-sonnet',)
