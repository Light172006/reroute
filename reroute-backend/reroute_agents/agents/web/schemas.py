"""Schemas for Web Research Agent outputs and place candidates."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class PlaceResearchItem(BaseModel):
    """A vetted place extracted from web research or verified sources."""

    name: str
    description: str = ""
    lat: float
    lng: float
    category: str = "sightseeing"
    setting: Literal["indoor", "outdoor", "mixed"] = "outdoor"
    avg_cost: Decimal = Decimal(100)
    avg_duration_min: int = 60
    opening_hours: dict[str, Any] | str | None = None
    source_url: str = "web://extracted"  # Default fallback if LLM omits source_url
    verified: bool = False  # True only if lat/lng were confirmed by geocoding
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    raw: dict[str, Any] = Field(default_factory=dict)
    seed: bool = False  # Flag so seed records and web records can coexist


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
