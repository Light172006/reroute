"""Itinerary API schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# Request schemas
class ItemUpdate(BaseModel):
    is_locked: Optional[bool] = None
    start_time: Optional[str] = None  # HH:MM
    end_time: Optional[str] = None  # HH:MM
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReorderRequest(BaseModel):
    day_index: int
    ordered_stable_keys: List[UUID]

    model_config = ConfigDict(from_attributes=True)


class RestoreVersionRequest(BaseModel):
    reason: str = "Restored from previous version"

    model_config = ConfigDict(from_attributes=True)


# Response schemas
class ItemOut(BaseModel):
    id: UUID
    stable_key: Optional[UUID] = None
    position: int
    title: str
    category: Optional[str] = None
    setting: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    est_cost: float
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_locked: bool
    flags: List[str] = []
    travel: dict
    place_id: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DaySummary(BaseModel):
    cost: float
    walking_min: int
    active_min: int


class DayOut(BaseModel):
    day_index: int
    date: Optional[str] = None
    summary: DaySummary
    items: List[ItemOut]

    model_config = ConfigDict(from_attributes=True)


class VersionOut(BaseModel):
    id: UUID
    version_no: int
    reason: str
    created_by: str
    total_cost: float
    summary: str
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ItineraryResponse(BaseModel):
    trip_id: UUID
    version: Optional[VersionOut] = None
    days: List[DayOut]

    model_config = ConfigDict(from_attributes=True)


class DiffItem(BaseModel):
    op: str  # add, delete, replace
    day: int
    stable_key: str
    before: Optional[ItemOut] = None
    after: Optional[ItemOut] = None
    why: str

    model_config = ConfigDict(from_attributes=True)