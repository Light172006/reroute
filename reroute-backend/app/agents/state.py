"""Agent state TypedDicts for LangGraph."""
from __future__ import annotations

from typing import Literal, Optional
from typing_extensions import TypedDict
from datetime import datetime
from uuid import UUID


class TripSpec(TypedDict):
    trip_id: str
    destination: str
    start_date: str  # ISO date
    end_date: str
    group_size: int
    budget_total: float
    currency: str
    pace: Literal["relaxed", "balanced", "packed"]
    vibe_tags: list[str]
    notes: Optional[str]


class DraftItem(TypedDict):
    stable_key: Optional[str]
    day_index: int
    position: int
    place_id: Optional[str]
    title: str
    category: str
    setting: Literal["indoor", "outdoor", "mixed"]
    start_time: str  # HH:MM
    end_time: str
    est_cost: float
    lat: Optional[float]
    lng: Optional[float]
    is_locked: bool
    travel_mode: Optional[str]
    travel_minutes: Optional[int]


class ItineraryDraft(TypedDict):
    items: list[DraftItem]
    summary: str


class Violation(TypedDict):
    code: Literal[
        "closed", "overlap", "travel_too_long", "over_budget",
        "day_too_long", "locked_changed"
    ]
    item_stable_key: Optional[str]
    day_index: Optional[int]
    detail: str


class DisruptionEvent(TypedDict):
    type: Literal["weather", "closure", "hours_conflict", "delay", "budget_overrun", "user_request"]
    severity: Literal["low", "medium", "high"]
    day_index: Optional[int]
    window_start: Optional[str]  # ISO datetime
    window_end: Optional[str]
    affected_stable_keys: list[str]
    summary: str
    source: str
    data: dict


class InjectedSignals(TypedDict):
    type: Literal["weather", "closure", "delay", "budget_overrun"]
    day_index: int
    params: dict


# Plan graph state
class PlanState(TypedDict):
    trip_id: str
    spec: TripSpec
    iteration: int
    places: list[dict]  # search_places results
    weather: dict  # get_weather_forecast result
    draft: Optional[ItineraryDraft]
    violations: list[Violation]
    message: str
    tool_calls: list[dict]


# Replan graph state
class ReplanState(TypedDict):
    trip_id: str
    base_version_id: str
    injected: Optional[InjectedSignals]
    disruption: Optional[DisruptionEvent]
    affected_keys: list[str]
    proposal_id: Optional[str]
    decision: Optional[Literal["approve", "reject", "alternatives"]]
    new_draft: Optional[ItineraryDraft]
    violations: list[Violation]
    message: str


# Chat graph state
class ChatState(TypedDict):
    trip_id: str
    message: str
    history: list[dict]  # previous messages
    response: str
    streaming_text: str