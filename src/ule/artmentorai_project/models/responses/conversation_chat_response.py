"""Response model for general art-learning chat (non-critique)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .analysis_response import AnalysisResponse


class ConversationChatResponse(BaseModel):
    """Conversational reply; may include structured critique when the turn was routed as feedback."""

    reply: str = Field(
        ...,
        min_length=1,
        max_length=12000,
        description='Assistant reply; markdown is allowed.',
    )
    analysis: AnalysisResponse | None = Field(
        None,
        description='Populated when the model routed this turn as artwork critique (text-only).',
    )
