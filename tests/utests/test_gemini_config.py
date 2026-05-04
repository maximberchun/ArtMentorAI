"""Unit tests for Gemini configuration."""

from ule.artmentorai_project.config.gemini_config import GeminiConfig


def test_model_try_chain_dedupes_and_trims() -> None:
    cfg = GeminiConfig(
        api_key='k',
        model_name='gemini-2.5-flash',
        model_fallbacks=' gemini-2.0-flash , gemini-2.5-flash ,gemini-1.5-flash',
    )
    assert cfg.model_try_chain() == (
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-1.5-flash',
    )


def test_model_try_chain_empty_fallbacks_is_primary_only() -> None:
    cfg = GeminiConfig(api_key='k', model_name='gemini-pro', model_fallbacks='')
    assert cfg.model_try_chain() == ('gemini-pro',)
