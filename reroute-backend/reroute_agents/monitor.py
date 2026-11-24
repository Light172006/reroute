"""Monitor Worker: Evaluates active trips using cheap deterministic rules and deduplicates."""

from __future__ import annotations

import logging
from uuid import UUID

from reroute_agents.gateway import get_or_create_repositories
from reroute_agents.repositories.interfaces import RepositoriesBundle
from reroute_agents.rules.impact_rules import analyze_impacts
from reroute_agents.state import DisruptionEvent, Signals
from reroute_agents.tools.weather import create_weather_tool

logger = logging.getLogger(__name__)


async def evaluate_trip(
    trip_id: UUID,
    repos: RepositoriesBundle | None = None,
) -> tuple[bool, list[DisruptionEvent]]:
    """Evaluate an active trip using cheap rules without invoking LLMs unless disruptions exist.

    Returns:
    - needs_replan (bool): True if at least one new, unaddressed disruption was detected.
    - new_disruptions (list[DisruptionEvent]): List of novel disruptions found.
    """
    bundle = await get_or_create_repositories(repos)

    spec = await bundle.trips.get_trip(trip_id)
    if not spec:
        return False, []

    curr_v = await bundle.itineraries.get_current_version(trip_id)
    if not curr_v:
        return False, []

    current_items = await bundle.itineraries.get_version_items(curr_v["id"])
    if not current_items:
        return False, []

    # 1. Cheap Weather Check
    weather_tool = create_weather_tool(bundle.cache)
    start_str = spec.start_date.isoformat()
    end_str = spec.end_date.isoformat()
    lat = current_items[0].lat or 27.04
    lng = current_items[0].lng or 88.26

    weather_res = await weather_tool.ainvoke(
        {
            "lat": lat,
            "lng": lng,
            "start_date": start_str,
            "end_date": end_str,
        }
    )

    weather_data = {}
    if weather_res.get("ok"):
        fc = weather_res.get("forecast", {})
        # Map hourly forecast into day_index format for impact rules
        num_days = (spec.end_date - spec.start_date).days + 1
        for day_num in range(1, num_days + 1):
            weather_data[str(day_num)] = {"hourly": fc.get("hourly", [])}

    # 2. Cheap Expenses Check
    expenses_summary = await bundle.expenses.get_expenses_summary(trip_id)

    signals = Signals(
        weather_forecast=weather_data,
        expenses_summary=expenses_summary,
    )

    # 3. Deterministic Impact Rule Evaluation (Pure Code, No LLM)
    disruptions = analyze_impacts(current_items, spec, signals)

    # 4. Fingerprint Deduplication
    new_disruptions: list[DisruptionEvent] = []
    for disruption in disruptions:
        if disruption.fingerprint:
            existing = await bundle.disruptions.get_disruption_by_fingerprint(
                trip_id, disruption.fingerprint
            )
            if existing:
                continue  # Already proposed or recorded; do not trigger duplicate replan
        new_disruptions.append(disruption)

    needs_replan = len(new_disruptions) > 0
    return needs_replan, new_disruptions
