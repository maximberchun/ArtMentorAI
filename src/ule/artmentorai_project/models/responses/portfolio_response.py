"""Response models for portfolio endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class PortfolioUploadResponse(BaseModel):
    """Response for POST /portfolio/upload."""

    ids: list[str] = Field(..., description='Created portfolio item IDs in upload order.')


class PortfolioHistoryItem(BaseModel):
    """A single entry returned by portfolio history/item endpoints.

    This maps 1:1 to the payload stored in Qdrant with a few normalized fields:
    - `id` is always included (stringified Qdrant point id)
    - `type` defaults to "critique" for older points missing the discriminator
    """

    id: str | None = Field(None, description='Qdrant point ID (uuid string).')
    type: Literal['critique', 'portfolio_item'] = Field(
        ...,
        description='Payload discriminator: critique or portfolio_item.',
    )

    user_id: str = Field(..., description='Owner user id.')
    filename: str | None = Field(None, description='Original filename (if provided).')
    timestamp: str | None = Field(
        None, description='ISO-8601 timestamp for when the item was stored.'
    )  # noqa: E501

    tags: list[str] = Field(default_factory=list, description='Optional tags applied to the item.')
    description: str | None = Field(
        None,
        description='Optional description for portfolio_item records (empty string if omitted).',
    )

    # Critique-only fields (present when type == "critique")
    score: int | None = Field(None, ge=1, le=10, description='Critique score (1-10).')
    summary: str | None = Field(None, description='Critique summary.')
    advice: str | None = Field(None, description='Critique advice.')
    goals_snapshot: str | None = Field(
        None, description='Compact snapshot of user goals at critique time.'
    )  # noqa: E501
    level_estimate: int | None = Field(
        None,
        ge=1,
        le=5,
        description='Derived level estimate (1-5) from score; null for portfolio items.',
    )
