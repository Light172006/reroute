"""Planner node: Generates structured day-by-day itinerary draft via LLM."""

from __future__ import annotations

import logging
from datetime import time, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from reroute_agents.events import draft_event, error_event, step_event
from reroute_agents.llm import FakeLLM, ResilientLLMChain, get_llm
from reroute_agents.state import DraftItem, ItineraryDraft, PlanState

logger = logging.getLogger(__name__)


def _load_planner_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "planner_v1.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "You are an itinerary planner. Generate a valid day-by-day ItineraryDraft."


def _build_deterministic_draft_from_candidates(state: PlanState) -> ItineraryDraft:
    """Fallback generator to construct a structurally valid draft if LLM is unavailable."""
    spec = state["spec"]
    candidates = state["candidates"]
    if not candidates:
        return ItineraryDraft(
            items=[],
            summary=f"No verified place candidates available for destination {spec.destination}.",
        )

    num_days = max((spec.end_date - spec.start_date).days + 1, 1)

    items: list[DraftItem] = []
    cand_idx = 0
    stops_per_day = 3 if spec.pace == "balanced" else (2 if spec.pace == "relaxed" else 4)

    # Standard schedule slots
    time_slots = [
        (time(9, 0), time(11, 0)),
        (time(11, 30), time(13, 0)),
        (time(14, 0), time(16, 0)),
        (time(16, 30), time(18, 0)),
    ]

    from reroute_agents.destinations.registry import resolve_destination

    cfg = resolve_destination(spec.destination)
    if cfg and cfg.id == "arunachal":
        fallback_lat, fallback_lng = 27.58, 92.20
    elif cfg and cfg.id == "north_sikkim":
        fallback_lat, fallback_lng = 27.50, 88.60
    elif cfg and cfg.id == "ladakh":
        fallback_lat, fallback_lng = 34.15, 77.57
    elif cfg and cfg.id == "meghalaya":
        fallback_lat, fallback_lng = 25.57, 91.88
    else:
        fallback_lat, fallback_lng = 27.04, 88.26

    for day in range(1, num_days + 1):
        day_date = spec.start_date + timedelta(days=day - 1)
        weekday = day_date.strftime("%a").lower()[:3]
        for pos in range(min(stops_per_day, len(time_slots))):
            start_t, end_t = time_slots[pos]
            start_m = start_t.hour * 60 + start_t.minute
            end_m = end_t.hour * 60 + end_t.minute

            # Select candidate that is open on this day and time window
            cand = None
            attempts = 0
            while attempts < len(candidates):
                c = candidates[cand_idx % len(candidates)]
                cand_idx += 1
                attempts += 1

                if c.opening_hours and isinstance(c.opening_hours, dict) and c.hours_confidence != "unknown":
                    day_wins = c.opening_hours.get(weekday)
                    if day_wins is None:
                        day_wins = c.opening_hours.get(day_date.strftime("%A").lower())
                    if day_wins is not None:
                        if len(day_wins) == 0:
                            continue
                        fits = False
                        for win in day_wins:
                            if len(win) == 2:
                                try:
                                    wh1, wm1 = map(int, win[0].split(":"))
                                    wh2, wm2 = map(int, win[1].split(":"))
                                    if (wh1 * 60 + wm1) <= start_m and end_m <= (wh2 * 60 + wm2):
                                        fits = True
                                        break
                                except Exception as ex:
                                    logger.debug("Failed parsing opening window: %s", ex)
                        if not fits:
                            continue
                cand = c
                break

            if not cand:
                cand = candidates[cand_idx % len(candidates)]

            item = DraftItem(
                stable_key=uuid4(),
                day_index=day,
                position=pos,
                place_id=cand.id,
                title=cand.name,
                category=cand.category,
                setting=cand.setting,
                start_time=start_t,
                end_time=end_t,
                est_cost=cand.avg_cost,
                lat=cand.lat if cand.lat is not None else fallback_lat,
                lng=cand.lng if cand.lng is not None else fallback_lng,
                is_locked=False,
                travel_mode="taxi" if pos > 0 else None,
                travel_minutes=20 if pos > 0 else 0,
            )
            items.append(item)

    return ItineraryDraft(
        items=items,
        summary=f"Curated {num_days}-day {spec.pace} itinerary across {spec.destination}.",
    )


def create_planner_node(llm_override: Any | None = None) -> Any:
    """Factory creating planner node with optional injected LLM."""
    system_prompt = _load_planner_prompt()

    async def planner_node(state: PlanState) -> dict[str, Any]:
        spec = state["spec"]
        candidates = state["candidates"]
        violations = state.get("violations", [])
        iteration = state.get("iteration", 0) + 1
        events = []

        if not candidates:
            events.append(
                error_event(
                    code="no_candidates_found",
                    message=f"No verified place candidates available for destination '{spec.destination}'. Cannot construct itinerary.",
                    recoverable=False,
                    node="planner",
                )
            )
            events.append(
                step_event(
                    node="planner",
                    message="Planning halted: no candidates found",
                    status="failed",
                )
            )
            return {
                "draft": ItineraryDraft(
                    items=[],
                    summary=f"No verified places found for {spec.destination}.",
                ),
                "iteration": iteration,
                "events": events,
            }

        num_days = max((spec.end_date - spec.start_date).days + 1, 1)
        step_msg = f"Building day-by-day itinerary (iteration {iteration})"
        if violations:
            step_msg = (
                f"Refining itinerary to resolve {len(violations)} issues (iteration {iteration})"
            )

        events.append(step_event(node="planner", message=step_msg, status="running"))

        # Construct prompt content
        candidate_summaries = [
            {
                "id": str(c.id),
                "name": c.name,
                "category": c.category,
                "setting": c.setting,
                "avg_cost": float(c.avg_cost),
                "avg_duration_min": c.avg_duration_min,
                "opening_hours": c.opening_hours,
                "hours_confidence": c.hours_confidence,
                "altitude_m": c.raw.get("altitude_m"),
                "permit_required": c.raw.get("permit_required", False),
            }
            for c in candidates
        ]

        violations_prompt = ""
        if violations:
            v_lines = [f"- Code {v.code} on Day {v.day_index}: {v.detail}" for v in violations]
            violations_prompt = (
                "\n\nPREVIOUS VALIDATION VIOLATIONS TO FIX:\n"
                + "\n".join(v_lines)
                + "\nYou must modify the schedule to fix all of the above violations."
            )

        user_content = (
            f"Destination: {spec.destination}\n"
            f"Trip duration: {num_days} days (from {spec.start_date} to {spec.end_date})\n"
            f"Pace: {spec.pace}\n"
            f"Budget Total: {spec.budget_total} {spec.currency}\n"
            f"Budget Per Day Cap: {spec.budget_per_day_cap}\n"
            f"Vibe tags: {', '.join(spec.vibe_tags)}\n"
            f"User notes: {spec.notes or 'None'}\n\n"
            f"Available Candidates:\n{candidate_summaries}\n"
            f"{violations_prompt}"
        )

        draft: ItineraryDraft
        llm = llm_override or get_llm("strong")

        if isinstance(llm, FakeLLM):
            runner = llm.with_structured_output(ItineraryDraft)
            try:
                draft = await runner.ainvoke(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ]
                )
            except Exception:
                draft = _build_deterministic_draft_from_candidates(state)
        elif isinstance(llm, ResilientLLMChain):
            try:
                draft = await llm.ainvoke_structured(
                    schema=ItineraryDraft,
                    prompt=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    events=events,
                    node_name="planner",
                )
            except Exception as e:
                logger.warning("LLM generation failed, falling back to deterministic: %s", e)
                draft = _build_deterministic_draft_from_candidates(state)
        else:
            try:
                runner = llm.with_structured_output(ItineraryDraft)
                draft = await runner.ainvoke(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ]
                )
            except Exception:
                draft = _build_deterministic_draft_from_candidates(state)

        # Emit draft event for timeline
        ready_days = sorted({it.day_index for it in draft.items})
        events.append(draft_event(days_ready=ready_days, node="planner"))
        events.append(
            step_event(
                node="planner",
                message=f"Draft completed with {len(draft.items)} stops across {len(ready_days)} days",
                status="done",
            )
        )

        return {
            "draft": draft,
            "iteration": iteration,
            "events": events,
        }

    return planner_node
