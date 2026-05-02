"""Request body for POST /analysis/chat."""

from pydantic import BaseModel, Field


class ConversationChatRequest(BaseModel):
    """User message for a general art-learning chat turn."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description='User question or message (not artwork critique requests).',
    )
    conversation_id: str | None = Field(
        default=None,
        description='Optional thread id for short-term context and persistence.',
    )
