"""Shared Pydantic domain models and LangGraph state schemas."""

from __future__ import annotations

import operator
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Annotated, Any, Literal, NotRequired, TypedDict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

# --- Domain Pydantic Models (Matching API Contract) ---


class TripSpec(BaseModel):
    trip_id: UUID
    destination: str
    start_date: date
    end_date: date
    group_size: int = 1
    budget_total: Decimal
    currency: str = "INR"
    pace: Literal["relaxed", "balanced", "packed"] = "balanced"
    vibe_tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    budget_per_day_cap: Decimal | None = None


class DraftItem(BaseModel):
    stable_key: UUID = Field(default_factory=uuid4)
    day_index: int
    position: int
    place_id: UUID | None = None
    title: str
    category: str
    setting: Literal["indoor", "outdoor", "mixed"]
    start_time: time | str
    end_time: time | str
    est_cost: Decimal = Field(default=Decimal(0))
    lat: float | None = None
    lng: float | None = None
    is_locked: bool = False
    travel_mode: str | None = None
    travel_minutes: int | None = None
    travel_distance_m: int | None = None
    flags: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_time(cls, v: Any) -> Any:
        if isinstance(v, str):
            parts = v.strip().split(":")
            if len(parts) >= 2:
                h = int(parts[0])
                m = int(parts[1][:2])
                s = int(parts[2][:2]) if len(parts) > 2 else 0
                return time(h, m, s)
        if isinstance(v, time) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class ItineraryDraft(BaseModel):
    items: list[DraftItem] = Field(default_factory=list)
    summary: str = ""


class Violation(BaseModel):
    code: Literal[
        "closed",
        "overlap",
        "travel_too_long",
        "over_budget",
        "day_too_long",
        "locked_changed",
        "unknown_place",
    ]
    item_stable_key: UUID | None = None
    day_index: int | None = None
    detail: str


class DisruptionEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    trip_id: UUID | None = None
    type: str  # weather, closure, hours_conflict, delay, budget_overrun, user_request
    severity: Literal["low", "medium", "high"] = "medium"
    day_index: int | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    affected_stable_keys: list[UUID] = Field(default_factory=list)
    summary: str
    source: str
    data: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str | None = None


class InjectedSignals(BaseModel):
    type: Literal["weather", "closure", "delay", "budget_overrun"]
    day_index: int
    params: dict[str, Any] = Field(default_factory=dict)


class DiffItem(BaseModel):
    op: Literal["replace", "remove", "add", "move"]
    day: int
    stable_key: UUID
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    why: str


class ReplanProposal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    trip_id: UUID
    run_id: UUID
    base_version_id: UUID
    status: Literal["pending", "approved", "rejected", "expired", "superseded"] = "pending"
    reason: str
    explanation: str
    disruptions: list[DisruptionEvent] = Field(default_factory=list)
    diff: list[DiffItem] = Field(default_factory=list)
    proposed_items: list[DraftItem] = Field(default_factory=list)
    cost_delta: Decimal = Field(default=Decimal(0))
    time_delta_min: int = 0
    items_changed: int = 0
    alternatives_of: UUID | None = None
    resulting_version_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlaceCandidate(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    external_id: str | None = None
    name: str
    city: str
    country: str = "IN"
    category: str
    setting: Literal["indoor", "outdoor", "mixed"] = "mixed"
    avg_cost: Decimal = Field(default=Decimal(0))
    currency: str = "INR"
    avg_duration_min: int = 60
    opening_hours: dict[str, list[list[str]]] | None = None
    hours_confidence: str = "unknown"
    lat: float
    lng: float
    rating: float | None = None
    tags: list[str] = Field(default_factory=list)
    description: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class Signals(BaseModel):
    weather_forecast: dict[str, Any] = Field(default_factory=dict)
    opening_hours_updates: dict[str, Any] = Field(default_factory=dict)
    travel_estimates: dict[str, Any] = Field(default_factory=dict)
    expenses_summary: dict[str, Any] = Field(default_factory=dict)
    injected: InjectedSignals | None = None


# --- Agent Event Definition ---


class AgentEvent(BaseModel):
    type: Literal[
        "step",
        "tool_call",
        "tool_result",
        "llm_call",
        "draft",
        "disruption",
        "proposal",
        "token",
        "error",
        "done",
    ]
    node: str | None = None
    message: str | None = None
    status: Literal["running", "done", "failed"] | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


# --- LangGraph Graph States ---


class PlanState(TypedDict):
    trip_id: str
    spec: TripSpec
    candidates: list[PlaceCandidate]
    draft: ItineraryDraft | None
    violations: list[Violation]
    iteration: int
    events: Annotated[list[AgentEvent], operator.add]


class ReplanState(TypedDict):
    trip_id: str
    run_id: str
    base_version_id: str
    spec: TripSpec | None
    signals: Signals
    disruptions: list[DisruptionEvent]
    affected_item_ids: list[str]
    current_items: list[DraftItem]
    draft: ItineraryDraft | None
    violations: list[Violation]
    proposal: ReplanProposal | None
    decision: Literal["approve", "reject", "alternatives"] | None
    iteration: int
    events: Annotated[list[AgentEvent], operator.add]


class ChatState(TypedDict):
    trip_id: str
    run_id: str
    messages: list[Any]
    current_items: list[DraftItem]
    spec: TripSpec | None
    proposal: ReplanProposal | None
    events: Annotated[list[AgentEvent], operator.add]
    iteration: NotRequired[int]
