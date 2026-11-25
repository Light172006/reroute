"""Shared Pydantic domain models and LangGraph state schemas."""

from __future__ import annotations

import json
import operator
import re
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


_VALID_CATEGORIES = frozenset({
    "sightseeing",
    "food",
    "culture",
    "nature",
    "nightlife",
    "shopping",
    "adventure",
    "transport",
    "stay",
    "other",
})
_VALID_TRAVEL_MODES = frozenset({"walk", "taxi", "bus", "train", "metro", "bike", "car"})


def normalize_category(value: Any) -> str:
    """Map free-form LLM category labels into canonical ItemType enum values."""
    if not value:
        return "sightseeing"
    low = str(value).strip().lower()
    if low in _VALID_CATEGORIES:
        return low
    checks: tuple[tuple[tuple[str, ...], str], ...] = (
        (("food", "restaurant", "cafe", "dining", "bakery", "culinary", "eat"), "food"),
        (("nightlife", "club", "bar", "pub", "party", "casino", "lounge"), "nightlife"),
        (("shop", "market", "bazaar", "mall", "flea", "souvenir"), "shopping"),
        (("adventure", "sport", "trek", "hike", "scuba", "rafting", "paragliding", "kayak", "dive", "safari"), "adventure"),
        (("beach", "nature", "lake", "waterfall", "falls", "park", "wildlife", "sanctuary", "mountain", "pass", "valley", "forest", "island", "river"), "nature"),
        (("culture", "heritage", "monastery", "temple", "church", "fort", "palace", "museum", "memorial", "monument", "historic", "religious", "shrine", "neighborhood"), "culture"),
        (("transport", "airport", "station", "ferry", "transit"), "transport"),
        (("stay", "hotel", "resort", "hostel", "homestay", "villa"), "stay"),
        (("sightseeing", "viewpoint", "landmark", "attraction", "tour"), "sightseeing"),
    )
    for keywords, target in checks:
        if any(k in low for k in keywords):
            return target
    return "sightseeing"


def normalize_travel_mode(value: Any) -> str | None:
    """Map free-form travel modes into canonical TransportMode enum values."""
    if value is None:
        return None
    low = str(value).strip().lower()
    if not low:
        return None
    if low in _VALID_TRAVEL_MODES:
        return low
    if any(k in low for k in ("walk", "foot", "stroll")):
        return "walk"
    if any(k in low for k in ("taxi", "cab", "uber", "ola", "auto", "rickshaw", "tuk")):
        return "taxi"
    if any(k in low for k in ("bus", "coach", "shuttle", "ferry", "boat")):
        return "bus"
    if any(k in low for k in ("train", "rail")):
        return "train"
    if any(k in low for k in ("metro", "subway")):
        return "metro"
    if any(k in low for k in ("bike", "cycle", "scooter", "scooty", "motorbike")):
        return "bike"
    if any(k in low for k in ("car", "drive", "jeep", "suv")):
        return "car"
    return "taxi"


class DraftItem(BaseModel):
    stable_key: UUID = Field(default_factory=uuid4)
    day_index: int
    position: int
    place_id: UUID | None = None
    title: str
    category: str
    setting: Literal["indoor", "outdoor", "mixed"]
    start_time: time
    end_time: time
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

    @field_validator("category", mode="before")
    @classmethod
    def _coerce_category(cls, v: Any) -> str:
        return normalize_category(v)

    @field_validator("travel_mode", mode="before")
    @classmethod
    def _coerce_travel_mode(cls, v: Any) -> str | None:
        return normalize_travel_mode(v)


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


_DAYS_ORDER = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_DAY_ALIASES: dict[str, str] = {
    "mon": "mon",
    "monday": "mon",
    "tue": "tue",
    "tues": "tue",
    "tuesday": "tue",
    "wed": "wed",
    "wednesday": "wed",
    "thu": "thu",
    "thur": "thu",
    "thurs": "thu",
    "thursday": "thu",
    "fri": "fri",
    "friday": "fri",
    "sat": "sat",
    "saturday": "sat",
    "sun": "sun",
    "sunday": "sun",
}
_TIME_RANGE_RE = re.compile(
    r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:-|–|—|\bto\b)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
    re.IGNORECASE,
)


def _parse_hhmm(raw: str) -> str | None:
    """Convert '9:00', '09:00', '9 AM', or '5:30 pm' into 'HH:MM' (24-hour)."""
    m = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*", raw, re.IGNORECASE)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    meridiem = (m.group(3) or "").lower()

    if meridiem:
        if hour < 1 or hour > 12:
            return None
        if meridiem == "am":
            hour = 0 if hour == 12 else hour
        elif meridiem == "pm":
            hour = 12 if hour == 12 else hour + 12
    elif hour == 24 and minute == 0:
        return "23:59"

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"


def _expand_days(day_expr: str) -> list[str]:
    """Expand expressions like 'Mon-Sun', 'Mon-Fri', 'Mon, Wed' into canonical day keys."""
    cleaned = re.sub(r"[^a-z,\-/\s]", " ", day_expr.lower()).strip()
    cleaned = re.sub(r"\bto\b", "-", cleaned)
    if not cleaned:
        return list(_DAYS_ORDER)
    if any(tok in cleaned for tok in ("daily", "everyday", "every day", "all days", "24/7")):
        return list(_DAYS_ORDER)
    if "weekday" in cleaned:
        return list(_DAYS_ORDER[:5])
    if "weekend" in cleaned:
        return list(_DAYS_ORDER[5:])

    days: list[str] = []
    for part in re.split(r"[,/&]+", cleaned):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = [b.strip() for b in part.split("-", 1)]
            start_day = _DAY_ALIASES.get(bounds[0])
            end_day = _DAY_ALIASES.get(bounds[1]) if len(bounds) == 2 else None
            if start_day and end_day:
                i1, i2 = _DAYS_ORDER.index(start_day), _DAYS_ORDER.index(end_day)
                idx = i1
                while True:
                    if _DAYS_ORDER[idx] not in days:
                        days.append(_DAYS_ORDER[idx])
                    if idx == i2:
                        break
                    idx = (idx + 1) % 7
                continue
        for word in part.split():
            d = _DAY_ALIASES.get(word)
            if d and d not in days:
                days.append(d)
    return days


def _parse_windows_str(raw: str) -> list[list[str]]:
    """Extract all [start_hhmm, end_hhmm] windows from a time string."""
    windows: list[list[str]] = []
    for m in _TIME_RANGE_RE.finditer(raw):
        start_t = _parse_hhmm(m.group(1))
        end_t = _parse_hhmm(m.group(2))
        if start_t and end_t:
            windows.append([start_t, end_t])
    return windows


def normalize_opening_hours(value: Any) -> dict[str, list[list[str]]] | None:
    """Coerce LLM-extracted string or partial dict opening_hours into canonical dict format."""
    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"unknown", "n/a", "na", "none", "null", "varies"}:
            return None
        if text.startswith("{"):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    value = parsed
            except json.JSONDecodeError:
                pass

    if isinstance(value, str):
        text = value.strip()
        lower = text.lower()
        if "24 hour" in lower or "24/7" in lower or "always open" in lower:
            return {d: [["00:00", "23:59"]] for d in _DAYS_ORDER}

        # Split segments on ';' or '\n', or commas followed by a day name
        segments = re.split(
            r"[;\n]+|,\s*(?=(?:mon|tue|wed|thu|fri|sat|sun)\b)",
            text,
            flags=re.IGNORECASE,
        )
        result: dict[str, list[list[str]]] = {}
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            windows = _parse_windows_str(seg)
            first_match = _TIME_RANGE_RE.search(seg)
            if first_match:
                day_prefix = seg[: first_match.start()].strip(" :")
                target_days = _expand_days(day_prefix) if day_prefix else list(_DAYS_ORDER)
                if not target_days:
                    target_days = list(_DAYS_ORDER)
                for d in target_days:
                    result.setdefault(d, []).extend(windows)
            elif "closed" in seg.lower():
                day_prefix = re.sub(r"\bclosed\b", "", seg, flags=re.IGNORECASE).strip(" :")
                for d in _expand_days(day_prefix):
                    result.setdefault(d, [])
        return result or None

    if isinstance(value, dict):
        result: dict[str, list[list[str]]] = {}
        for raw_key, raw_val in value.items():
            key_str = str(raw_key).strip().lower()
            if key_str in {"daily", "everyday", "all", "all_days"}:
                target_days = list(_DAYS_ORDER)
            elif key_str in _DAY_ALIASES:
                target_days = [_DAY_ALIASES[key_str]]
            elif "-" in key_str or "," in key_str:
                target_days = _expand_days(key_str)
            else:
                continue

            day_windows: list[list[str]] = []
            if raw_val is None:
                day_windows = []
            elif isinstance(raw_val, str):
                if "24" in raw_val and "hour" in raw_val.lower():
                    day_windows = [["00:00", "23:59"]]
                elif "closed" not in raw_val.lower():
                    day_windows = _parse_windows_str(raw_val)
            elif isinstance(raw_val, list):
                if (
                    len(raw_val) == 2
                    and all(isinstance(x, str) for x in raw_val)
                ):
                    s_t, e_t = _parse_hhmm(raw_val[0]), _parse_hhmm(raw_val[1])
                    if s_t and e_t:
                        day_windows = [[s_t, e_t]]
                else:
                    for item in raw_val:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            s_t = _parse_hhmm(str(item[0]))
                            e_t = _parse_hhmm(str(item[1]))
                            if s_t and e_t:
                                day_windows.append([s_t, e_t])
                        elif isinstance(item, str):
                            day_windows.extend(_parse_windows_str(item))

            for d in target_days:
                result[d] = day_windows
        return result or None

    return None


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

    @field_validator("opening_hours", mode="before")
    @classmethod
    def _coerce_opening_hours(cls, v: Any) -> dict[str, list[list[str]]] | None:
        return normalize_opening_hours(v)

    @field_validator("category", mode="before")
    @classmethod
    def _coerce_category(cls, v: Any) -> str:
        return normalize_category(v)


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
