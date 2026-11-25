"""Schemas for Web Research Agent outputs and place candidates."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from reroute_agents.state import normalize_category


def _coerce_decimal_cost(value: Any) -> Decimal:
    """Parse LLM-returned costs like 'Free entry' or '₹800–₹1,500' into Decimal."""
    if value is None:
        return Decimal(0)
    if isinstance(value, Decimal):
        return max(value, Decimal(0))
    if isinstance(value, (int, float)):
        return Decimal(str(max(0, value)))
    if isinstance(value, str):
        text = value.strip().lower()
        if not text or "free" in text or "no fee" in text:
            return Decimal(0)
        # Strip thousand separators and extract first numeric amount
        cleaned = text.replace(",", "")
        m = re.search(r"\d+(?:\.\d+)?", cleaned)
        if m:
            try:
                return Decimal(m.group(0))
            except InvalidOperation:
                return Decimal(100)
        return Decimal(0)
    return Decimal(100)


class PlaceResearchItem(BaseModel):
    """A vetted place extracted from web research or verified sources."""

    name: str
    description: str = ""
    lat: float | None = 0.0
    lng: float | None = 0.0
    category: str = "sightseeing"
    setting: Literal["indoor", "outdoor", "mixed"] | str | None = "outdoor"
    avg_cost: Decimal | float | int | str | None = None
    avg_duration_min: int | None = 60
    opening_hours: dict[str, Any] | str | None = None
    source_url: str | None = "web://extracted"  # Default fallback if LLM omits source_url
    verified: bool | None = False  # True only if lat/lng were confirmed by geocoding
    confidence: float | None = Field(default=0.8, ge=0.0, le=1.0)
    raw: dict[str, Any] = Field(default_factory=dict)
    seed: bool = False  # Flag so seed records and web records can coexist

    @field_validator("category", mode="before")
    @classmethod
    def _parse_category(cls, v: Any) -> str:
        return normalize_category(v)

    @field_validator("setting", mode="before")
    @classmethod
    def _parse_setting(cls, v: Any) -> str:
        if isinstance(v, str):
            low = v.strip().lower()
            if low in ("indoor", "outdoor", "mixed"):
                return low
        return "outdoor"

    @field_validator("avg_cost", mode="before")
    @classmethod
    def _parse_avg_cost(cls, v: Any) -> Decimal:
        return _coerce_decimal_cost(v)

    @field_validator("avg_duration_min", mode="before")
    @classmethod
    def _parse_avg_duration(cls, v: Any) -> int:
        if v is None:
            return 60
        if isinstance(v, (int, float)):
            return max(15, min(int(v), 720))
        if isinstance(v, str):
            m = re.search(r"\d+", v)
            if m:
                val = int(m.group(0))
                if "hour" in v.lower() and val <= 12:
                    val *= 60
                return max(15, min(val, 720))
        return 60

    @field_validator("lat", "lng", mode="before")
    @classmethod
    def _parse_coords(cls, v: Any) -> float:
        if v is None or v == "":
            return 0.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    @field_validator("confidence", mode="before")
    @classmethod
    def _parse_confidence(cls, v: Any) -> float:
        if v is None:
            return 0.8
        try:
            val = float(v)
            return max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            return 0.8


class WebExtractionSchema(BaseModel):
    """Pydantic schema for structured LLM extraction of place candidates."""

    places: list[PlaceResearchItem] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """Structured output returned by the Web Research Agent."""

    destination: str
    places: list[PlaceResearchItem] = Field(default_factory=list)
    source: str = "web"  # "web", "seed_fallback", "mock"
    query: str = ""
    summary: str = ""
    fallback: bool = False
    tool_counts: dict[str, int] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)
