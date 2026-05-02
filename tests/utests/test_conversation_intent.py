"""Unit tests for text-only critique vs chat intent heuristics."""

from __future__ import annotations

from ule.artmentorai_project.utils.conversation_intent import is_text_only_critique_intent


def test_book_question_is_chat_not_critique_intent() -> None:
    assert not is_text_only_critique_intent(
        'What book do you recommend for learning drawing?',
    )


def test_critique_phrases_route_to_critique() -> None:
    assert is_text_only_critique_intent('Please critique this artwork')
    assert is_text_only_critique_intent("What's wrong with my proportions?")
    assert is_text_only_critique_intent('Rate my sketch')


def test_whitespace_only_is_false() -> None:
    assert not is_text_only_critique_intent('   ')
