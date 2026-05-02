"""Response model for general art-learning chat (non-critique)."""

from pydantic import BaseModel, Field


class ConversationChatResponse(BaseModel):
    """Plain conversational reply for Q&A turns (books, methods, theory, etc.)."""

    reply: str = Field(
        ...,
        min_length=1,
        max_length=12000,
        description='Assistant reply; markdown is allowed.',
    )
