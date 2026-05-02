"""Heuristics for routing text-only conversation turns to critique vs general chat."""

from __future__ import annotations

import re

_CRITIQUE_HINT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'\b(critique|criticize|criticise)\b', re.IGNORECASE),
    re.compile(r'\b(rate|review|roast)\s+my\b', re.IGNORECASE),
    re.compile(r'\bfeedback\s+on\s+(my|this|the|it)\b', re.IGNORECASE),
    re.compile(
        r"\bwhat(?:'s| is)\s+wrong\s+with\s+(my|this|these|it)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r'\bhow\s+can\s+i\s+improve\s+(this|it|my|the)\b',
        re.IGNORECASE,
    ),
    re.compile(r'\bplease\s+(critique|criticize|criticise|review)\b', re.IGNORECASE),
    re.compile(r'\b(look|check)\s+at\s+my\b', re.IGNORECASE),
)


def is_text_only_critique_intent(message: str) -> bool:
    """Return True when a text-only turn should use structured critique, not general chat.

    Mirrors ``frontend/src/lib/conversationIntent.ts`` — keep rules in sync.
    """
    normalized = ' '.join(message.strip().split())
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _CRITIQUE_HINT_PATTERNS)
