"""Structured output for routing a conversation turn (critique vs Q&A)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConversationTurnIntent(BaseModel):
    """Whether the user wants artwork feedback or general art-learning Q&A."""

    mode: Literal['critique', 'question_answering'] = Field(
        ...,
        description=(
            'critique: feedback on the user\'s own work (described or uploaded). '
            'question_answering: general study questions without evaluating their piece.'
        ),
    )
