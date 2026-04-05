"""Row shapes returned from Supabase Postgres tables."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProfileRow(BaseModel):
    """Row from ``public.profiles``."""

    model_config = ConfigDict(extra='ignore')

    user_id: str
    goals: list[str] = Field(default_factory=list)
    preferred_styles: list[str] = Field(default_factory=list)
    disliked_styles: list[str] = Field(default_factory=list)
    favorite_artists: list[str] = Field(default_factory=list)
    experience_level: str = 'beginner'
    retain_memory: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class ImageAssetRow(BaseModel):
    """Row from ``public.image_assets``."""

    model_config = ConfigDict(extra='ignore')

    id: str
    user_id: str
    storage_bucket: str
    storage_object_path: str
    mime_type: str | None = None
    original_filename: str | None = None
    byte_size: int | None = None
    created_at: datetime | None = None
    deleted_at: datetime | None = None


class CritiqueRow(BaseModel):
    """Row from ``public.critiques``."""

    model_config = ConfigDict(extra='ignore')

    id: str
    user_id: str
    image_asset_id: str | None = None
    artwork_filename: str | None = None
    summary: str
    score: int
    technical_errors: list[Any] = Field(default_factory=list)
    constructive_advice: str
    tags: list[str] = Field(default_factory=list)
    goals_snapshot: str | None = None
    vector_point_id: str | None = None
    created_at: datetime | None = None
    deleted_at: datetime | None = None


class PortfolioItemRow(BaseModel):
    """Row from ``public.portfolio_items``."""

    model_config = ConfigDict(extra='ignore')

    id: str
    user_id: str
    image_asset_id: str
    filename: str
    tags: list[str] = Field(default_factory=list)
    description: str = ''
    vector_point_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class ProgressSnapshotRow(BaseModel):
    """Row from ``public.progress_snapshots``."""

    model_config = ConfigDict(extra='ignore')

    id: str
    user_id: str
    critique_id: str | None = None
    rubric_key: str
    rubric_version: str = '1.0'
    dimension_scores: dict[str, Any] = Field(default_factory=dict)
    aggregate_score: float | None = None
    narrative: str | None = None
    created_at: datetime | None = None
    deleted_at: datetime | None = None


__all__ = [
    'CritiqueRow',
    'ImageAssetRow',
    'PortfolioItemRow',
    'ProfileRow',
    'ProgressSnapshotRow',
]
