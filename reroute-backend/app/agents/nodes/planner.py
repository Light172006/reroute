"""Planner node: creates day-by-day itinerary from places and constraints."""
from __future__ import annotations

from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.state import PlanState, ItineraryDraft, DraftItem


class PlannerOutput(BaseModel):
    items: list[DraftItem] = Field(description="Day-by-day itinerary items")
    summary: str = Field(description="Brief summary of the itinerary")


SYSTEM_PROMPT = """You are a travel planner. Create an optimized day-by-day itinerary from the available places.
Consider: opening hours, travel time, budget, pace, and vibe preferences.
Each item needs: day_index (1-based), position (0-based within day), place_id, title, category, setting,
start_time (HH:MM), end_time (HH:MM), est_cost, lat, lng, is_locked=false, travel_mode, travel_minutes.
Return ONLY the JSON object matching the schema."""


def planner(llm: Optional[BaseChatModel] = None):
    """Create the planner node function."""
    async def _node(state: PlanState) -> PlanState:
        spec = state.get("spec", {})
        places = state.get("places", [])
        weather = state.get("weather", {})
        pace = spec.get("pace", "balanced")
        budget_total = float(spec.get("budget_total", 0))

        # If no LLM or mock mode, create a simple deterministic plan
        if not llm:
            draft = _mock_plan(places, spec, weather, pace, budget_total)
            return {"draft": draft, "message": "Mock itinerary created"}

        try:
            structured_llm = llm.with_structured_output(PlannerOutput)
            prompt = f"""
TripSpec: {spec}
Places: {places}
Weather: {weather}
Pace: {pace}
Budget: {budget_total}
"""
            result = await structured_llm.ainvoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ])
            draft = {"items": [item.model_dump() for item in result.items], "summary": result.summary}
        except Exception:
            draft = _mock_plan(places, spec, weather, pace, budget_total)

        return {"draft": draft, "message": "Itinerary draft created"}

    return _node


def _mock_plan(places: list, spec: dict, weather: dict, pace: str, budget: float) -> dict:
    """Create a mock itinerary for demo mode."""
    destination = spec.get("destination", "Darjeeling")
    start_date = spec.get("start_date", "2026-12-12")
    end_date = spec.get("end_date", "2026-12-14")
    group_size = spec.get("group_size", 3)

    from datetime import datetime
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    num_days = (end - start).days + 1

    # Filter outdoor/indoor based on weather
    outdoor_places = [p for p in places if p.get("setting") == "outdoor"]
    indoor_places = [p for p in places if p.get("setting") in ("indoor", "mixed")]

    items = []
    place_idx = 0

    for day in range(1, num_days + 1):
        # Morning outdoor (if weather permits)
        day_weather = weather.get(f"day_{day}", {})
        precip_probs = day_weather.get("precip_prob", [20] * 24)
        # Check if afternoon has high precip
        afternoon_rain = max(precip_probs[12:18]) if len(precip_probs) >= 18 else 20

        pos = 0
        # Morning item
        if outdoor_places and place_idx < len(outdoor_places):
            p = outdoor_places[place_idx]
            place_idx += 1
            items.append(DraftItem(
                stable_key=None,
                day_index=day,
                position=pos,
                place_id=p.get("id"),
                title=p.get("name"),
                category=p.get("category"),
                setting=p.get("setting"),
                start_time="09:00",
                end_time="10:30",
                est_cost=p.get("avg_cost", 100) * group_size,
                lat=p.get("lat"),
                lng=p.get("lng"),
                is_locked=False,
                travel_mode="taxi",
                travel_minutes=15,
            ))
            pos += 1

        # Midday item
        if indoor_places and place_idx < len(indoor_places):
            p = indoor_places[place_idx]
            place_idx += 1
            items.append(DraftItem(
                stable_key=None,
                day_index=day,
                position=pos,
                place_id=p.get("id"),
                title=p.get("name"),
                category=p.get("category"),
                setting=p.get("setting"),
                start_time="11:00",
                end_time="12:30",
                est_cost=p.get("avg_cost", 100) * group_size,
                lat=p.get("lat"),
                lng=p.get("lng"),
                is_locked=False,
                travel_mode="walk",
                travel_minutes=10,
            ))
            pos += 1

        # Lunch
        food_places = [p for p in places if p.get("category") == "food"]
        if food_places:
            p = food_places[0]
            items.append(DraftItem(
                stable_key=None,
                day_index=day,
                position=pos,
                place_id=p.get("id"),
                title=p.get("name"),
                category=p.get("category"),
                setting=p.get("setting"),
                start_time="13:00",
                end_time="14:00",
                est_cost=p.get("avg_cost", 200) * group_size,
                lat=p.get("lat"),
                lng=p.get("lng"),
                is_locked=False,
                travel_mode="walk",
                travel_minutes=5,
            ))
            pos += 1

        # Afternoon - check weather, prefer indoor if rain
        if afternoon_rain >= 60 and indoor_places and place_idx < len(indoor_places):
            p = indoor_places[place_idx]
            place_idx += 1
        elif outdoor_places and place_idx < len(outdoor_places):
            p = outdoor_places[place_idx]
            place_idx += 1
        else:
            p = None

        if p:
            items.append(DraftItem(
                stable_key=None,
                day_index=day,
                position=pos,
                place_id=p.get("id"),
                title=p.get("name"),
                category=p.get("category"),
                setting=p.get("setting"),
                start_time="14:30",
                end_time="16:00",
                est_cost=p.get("avg_cost", 100) * group_size,
                lat=p.get("lat"),
                lng=p.get("lng"),
                is_locked=False,
                travel_mode="taxi",
                travel_minutes=15,
            ))
            pos += 1

        # Evening
        if indoor_places and place_idx < len(indoor_places):
            p = indoor_places[place_idx]
            place_idx += 1
            items.append(DraftItem(
                stable_key=None,
                day_index=day,
                position=pos,
                place_id=p.get("id"),
                title=p.get("name"),
                category=p.get("category"),
                setting=p.get("setting"),
                start_time="18:00",
                end_time="20:00",
                est_cost=p.get("avg_cost", 100) * group_size,
                lat=p.get("lat"),
                lng=p.get("lng"),
                is_locked=False,
                travel_mode="taxi",
                travel_minutes=15,
            ))

    total_cost = sum(item.get("est_cost", 0) for item in items)
    return {
        "items": [item if isinstance(item, dict) else item for item in items],
        "summary": f"{num_days}-day {destination} itinerary, est. cost: {total_cost:.0f}",
    }