"""Response models for private user progress endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class ProgressSnapshotSummary(BaseModel):
    """Compact view of a progress snapshot for dashboard usage."""

    id: str
    critique_id: str | None = None
    rubric_key: str
    aggregate_score: float | None = None
    created_at: datetime | None = None


class ProgressMeResponse(BaseModel):
    """Private progression state for the authenticated user."""

    user_id: str
    total_xp: int = Field(default=0, ge=0)
    current_level: int = Field(default=1, ge=1)
    streak_count: int = Field(default=0, ge=0)
    streak_last_date: date | None = None
    badges: list[str] = Field(default_factory=list)
    latest_snapshot: ProgressSnapshotSummary | None = None
    recent_snapshots: list[ProgressSnapshotSummary] = Field(default_factory=list)
