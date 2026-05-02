"""Row shapes returned from Supabase Postgres tables."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003
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
    conversation_id: str | None = None
    image_asset_id: str | None = None
    artwork_filename: str | None = None
    summary: str
    score: int | None = None
    rubric_anchors: list[Any] = Field(default_factory=list)
    prioritized_issues: list[Any] = Field(default_factory=list)
    root_causes: list[Any] = Field(default_factory=list)
    targeted_drills: list[Any] = Field(default_factory=list)
    readiness_gate: str = ''
    confidence: float = 0.0
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


class VectorSyncJobRow(BaseModel):
    """Row from ``public.vector_sync_jobs`` (Qdrant sync outbox)."""

    model_config = ConfigDict(extra='ignore')

    id: str
    entity_kind: str
    entity_id: str
    operation: str
    status: str
    attempt_count: int = 0
    last_error: str | None = None
    next_attempt_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


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


class UserProgressRow(BaseModel):
    """Row from ``public.user_progress``."""

    model_config = ConfigDict(extra='ignore')

    user_id: str
    total_xp: int = 0
    current_level: int = 1
    streak_count: int = 0
    streak_last_date: date | None = None
    badges: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConversationRow(BaseModel):
    """Row from ``public.conversations``."""

    model_config = ConfigDict(extra='ignore')

    id: str
    user_id: str
    title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class ConversationMessageRow(BaseModel):
    """Row from ``public.conversation_messages``."""

    model_config = ConfigDict(extra='ignore')

    id: str
    conversation_id: str
    user_id: str
    role: str
    content: str
    critique_id: str | None = None
    created_at: datetime | None = None
    deleted_at: datetime | None = None


__all__ = [
    'ConversationMessageRow',
    'ConversationRow',
    'CritiqueRow',
    'ImageAssetRow',
    'PortfolioItemRow',
    'ProfileRow',
    'ProgressSnapshotRow',
    'UserProgressRow',
    'VectorSyncJobRow',
]
