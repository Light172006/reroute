# app/api/schemas/trip.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TripBase(BaseModel):
    title: str
    destination: str
    start_date: date
    end_date: date
    group_size: int = 1
    budget_total: float = 0.0
    budget_per_day_cap: Optional[float] = None
    currency: str = "INR"
    pace: str = "balanced"
    vibe_tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class TripCreate(TripBase):
    pass


class TripUpdate(BaseModel):
    title: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    group_size: Optional[int] = None
    budget_total: Optional[float] = None
    budget_per_day_cap: Optional[float] = None
    currency: Optional[str] = None
    pace: Optional[str] = None
    vibe_tags: Optional[List[str]] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class TripOut(TripBase):
    id: UUID
    user_id: Optional[UUID] = None
    dest_lat: Optional[float] = None
    dest_lng: Optional[float] = None
    status: str = "draft"
    current_version_id: Optional[UUID] = None
    last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
