"""Deterministic impact analysis rules and disruption event generation."""

from __future__ import annotations

import hashlib
from datetime import datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from reroute_agents.config import settings
from reroute_agents.state import DisruptionEvent, DraftItem, Signals, TripSpec


def compute_disruption_fingerprint(
    disruption_type: str,
    day_index: int | None,
    affected_keys: list[UUID],
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> str:
    """Compute a stable hash for deduplicating disruption events."""
    keys_str = ",".join(sorted(str(k) for k in affected_keys))
    w_start_str = window_start.isoformat() if window_start else ""
    w_end_str = window_end.isoformat() if window_end else ""
    raw = f"{disruption_type}|{day_index}|{keys_str}|{w_start_str}|{w_end_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def analyze_impacts(
    items: list[DraftItem],
    spec: TripSpec,
    signals: Signals,
    places_metadata: dict[UUID, dict[str, Any]] | None = None,
) -> list[DisruptionEvent]:
    """Pure function evaluating external and injected signals against an itinerary.

    Detects:
    1. Weather: precip_prob >= 0.60, snowfall, or low visibility on outdoor/mixed stops.
    2. Closure / Hours: Place closures, pass/road closures, or updated operating hours.
    3. Delay: Travel duration increases by >= 30 min affecting downstream stops.
    4. Budget overrun: Actual expenses exceed planned expenses by >= 10%.
    """
    disruptions: list[DisruptionEvent] = []
    _ = places_metadata

    items_by_day: dict[int, list[DraftItem]] = {}
    for item in items:
        items_by_day.setdefault(item.day_index, []).append(item)

    # 1. Weather Signals (Real or Injected)
    weather_data = signals.weather_forecast
    injected = signals.injected

    if injected and injected.type == "weather":
        day_idx = injected.day_index
        day_items = items_by_day.get(day_idx, [])
        precip = float(injected.params.get("precip_prob", 0.8))
        from_str = str(injected.params.get("from", "00:00"))
        to_str = str(injected.params.get("to", "23:59"))
        fh, fm = map(int, from_str.split(":"))
        th, tm = map(int, to_str.split(":"))
        win_start_t = time(fh, fm)
        win_end_t = time(th, tm)

        injected_weather_affected: list[UUID] = []
        for it in day_items:
            if it.setting in ("outdoor", "mixed"):
                if not (it.end_time <= win_start_t or it.start_time >= win_end_t):
                    injected_weather_affected.append(it.stable_key)

        if injected_weather_affected and precip >= settings.precip_prob_threshold:
            pct = int(precip * 100)
            summary = f"Precipitation likely on Day {day_idx} ({pct}%, {from_str}-{to_str})"
            fp = compute_disruption_fingerprint("weather", day_idx, injected_weather_affected)
            disruptions.append(
                DisruptionEvent(
                    id=uuid4(),
                    trip_id=spec.trip_id,
                    type="weather",
                    severity="high" if precip >= 0.8 else "medium",
                    day_index=day_idx,
                    affected_stable_keys=injected_weather_affected,
                    summary=summary,
                    source="injected" if injected else "open-meteo",
                    data={"precip_prob": precip, "window": f"{from_str}-{to_str}"},
                    fingerprint=fp,
                )
            )

    elif weather_data:
        for day_str, day_fc in weather_data.items():
            try:
                day_idx = int(day_str)
            except ValueError:
                continue
            day_items = items_by_day.get(day_idx, [])
            hourly = day_fc.get("hourly", [])
            forecast_affected_set: set[UUID] = set()
            max_precip = 0.0
            severe_snow = False
            low_vis = False

            for h in hourly:
                p_prob = float(h.get("precip_prob", 0.0))
                snow = float(h.get("snowfall", 0.0))
                vis = int(h.get("visibility", 10000))
                hour_val = int(h.get("hour", 0))
                h_start = time(hour_val, 0)
                h_end = time(min(hour_val + 1, 23), 59)

                if p_prob >= settings.precip_prob_threshold or snow > 0.5 or vis < 1000:
                    for it in day_items:
                        if it.setting in ("outdoor", "mixed"):
                            if not (it.end_time <= h_start or it.start_time >= h_end):
                                forecast_affected_set.add(it.stable_key)
                                max_precip = max(max_precip, p_prob)
                                if snow > 0.5:
                                    severe_snow = True
                                if vis < 1000:
                                    low_vis = True

            if forecast_affected_set:
                pct = int(max_precip * 100)
                detail_reasons: list[str] = []
                if max_precip >= settings.precip_prob_threshold:
                    detail_reasons.append(f"rain {pct}%")
                if severe_snow:
                    detail_reasons.append("snowfall")
                if low_vis:
                    detail_reasons.append("low visibility")
                summary = f"Adverse weather on Day {day_idx}: {', '.join(detail_reasons)}"
                keys_list = list(forecast_affected_set)
                fp = compute_disruption_fingerprint("weather", day_idx, keys_list)
                disruptions.append(
                    DisruptionEvent(
                        id=uuid4(),
                        trip_id=spec.trip_id,
                        type="weather",
                        severity="high" if (max_precip >= 0.8 or severe_snow) else "medium",
                        day_index=day_idx,
                        affected_stable_keys=keys_list,
                        summary=summary,
                        source="open-meteo",
                        data={"precip_prob": max_precip, "snow": severe_snow, "low_vis": low_vis},
                        fingerprint=fp,
                    )
                )

    # 2. Closure / Hours Disruptions
    closure_updates = signals.opening_hours_updates
    if injected and injected.type == "closure":
        day_idx = injected.day_index
        day_items = items_by_day.get(day_idx, [])
        affected_place_id = injected.params.get("place_id")
        reason = str(injected.params.get("reason", "Attraction or pass closed unexpectedly"))
        injected_closure_affected: list[UUID] = [
            it.stable_key
            for it in day_items
            if (affected_place_id and str(it.place_id) == str(affected_place_id))
            or (not affected_place_id and it.position == 0)
        ]
        if injected_closure_affected:
            fp = compute_disruption_fingerprint("closure", day_idx, injected_closure_affected)
            disruptions.append(
                DisruptionEvent(
                    id=uuid4(),
                    trip_id=spec.trip_id,
                    type="closure",
                    severity="high",
                    day_index=day_idx,
                    affected_stable_keys=injected_closure_affected,
                    summary=f"Closure on Day {day_idx}: {reason}",
                    source="injected",
                    data=injected.params,
                    fingerprint=fp,
                )
            )
    elif closure_updates:
        for p_id_str, update in closure_updates.items():
            if update.get("is_closed") or update.get("closed"):
                reason = str(update.get("reason", "Place closed"))
                for day_idx, day_items in items_by_day.items():
                    catalog_closure_affected = [
                        it.stable_key for it in day_items if str(it.place_id) == p_id_str
                    ]
                    if catalog_closure_affected:
                        fp = compute_disruption_fingerprint(
                            "closure", day_idx, catalog_closure_affected
                        )
                        disruptions.append(
                            DisruptionEvent(
                                id=uuid4(),
                                trip_id=spec.trip_id,
                                type="closure",
                                severity="high",
                                day_index=day_idx,
                                affected_stable_keys=catalog_closure_affected,
                                summary=f"Closure on Day {day_idx}: {reason}",
                                source="catalog_update",
                                data=update,
                                fingerprint=fp,
                            )
                        )

    # 3. Delay Signals (Travel delay >= 30 min)
    travel_estimates = signals.travel_estimates
    if injected and injected.type == "delay":
        day_idx = injected.day_index
        day_items = items_by_day.get(day_idx, [])
        delay_min = int(injected.params.get("delay_minutes", 45))
        if delay_min >= settings.delay_threshold_minutes and len(day_items) >= 2:
            injected_delay_affected = [it.stable_key for it in day_items[1:]]
            fp = compute_disruption_fingerprint("delay", day_idx, injected_delay_affected)
            disruptions.append(
                DisruptionEvent(
                    id=uuid4(),
                    trip_id=spec.trip_id,
                    type="delay",
                    severity="high" if delay_min >= 60 else "medium",
                    day_index=day_idx,
                    affected_stable_keys=injected_delay_affected,
                    summary=f"Travel delay of {delay_min} min on Day {day_idx} affecting downstream stops",
                    source="injected",
                    data={"delay_minutes": delay_min},
                    fingerprint=fp,
                )
            )
    elif travel_estimates:
        for est in travel_estimates.get("legs", []):
            day_idx = est.get("day_index")
            new_min = int(est.get("new_minutes", 0))
            planned_min = int(est.get("planned_minutes", 0))
            diff = new_min - planned_min
            if diff >= settings.delay_threshold_minutes:
                day_items = items_by_day.get(day_idx, [])
                leg_idx = int(est.get("leg_index", 1))
                route_delay_affected = [it.stable_key for it in day_items[leg_idx:]]
                if route_delay_affected:
                    fp = compute_disruption_fingerprint("delay", day_idx, route_delay_affected)
                    disruptions.append(
                        DisruptionEvent(
                            id=uuid4(),
                            trip_id=spec.trip_id,
                            type="delay",
                            severity="high" if diff >= 60 else "medium",
                            day_index=day_idx,
                            affected_stable_keys=route_delay_affected,
                            summary=f"Significant travel delay (+{diff} min) on Day {day_idx}",
                            source="ors",
                            data={"delay_minutes": diff},
                            fingerprint=fp,
                        )
                    )

    # 4. Budget Overrun Signals (Actual > planned by >= 10%)
    expenses_summary = signals.expenses_summary
    if injected and injected.type == "budget_overrun":
        overrun_pct = float(injected.params.get("overrun_pct", 0.15))
        if overrun_pct >= settings.budget_overrun_pct_threshold:
            injected_budget_affected = [
                it.stable_key for it in items if not it.is_locked and it.est_cost > Decimal(0)
            ]
            fp = compute_disruption_fingerprint("budget_overrun", None, injected_budget_affected)
            pct_display = int(overrun_pct * 100)
            disruptions.append(
                DisruptionEvent(
                    id=uuid4(),
                    trip_id=spec.trip_id,
                    type="budget_overrun",
                    severity="high" if overrun_pct >= 0.2 else "medium",
                    day_index=None,
                    affected_stable_keys=injected_budget_affected,
                    summary=f"Budget overrun by {pct_display}% requires cost reduction on upcoming activities",
                    source="injected",
                    data={"overrun_pct": overrun_pct},
                    fingerprint=fp,
                )
            )
    elif expenses_summary:
        actual_total = Decimal(
            str(expenses_summary.get("actual_total", expenses_summary.get("total", 0)))
        )
        planned_total = sum((it.est_cost for it in items), Decimal(0))
        if planned_total > 0 and actual_total > planned_total:
            overrun_ratio = float((actual_total - planned_total) / planned_total)
            if overrun_ratio >= settings.budget_overrun_pct_threshold:
                expense_budget_affected = [
                    it.stable_key for it in items if not it.is_locked and it.est_cost > Decimal(0)
                ]
                fp = compute_disruption_fingerprint("budget_overrun", None, expense_budget_affected)
                pct_display = int(overrun_ratio * 100)
                disruptions.append(
                    DisruptionEvent(
                        id=uuid4(),
                        trip_id=spec.trip_id,
                        type="budget_overrun",
                        severity="high" if overrun_ratio >= 0.2 else "medium",
                        day_index=None,
                        affected_stable_keys=expense_budget_affected,
                        summary=f"Actual spending exceeds planned budget by {pct_display}%",
                        source="expenses_service",
                        data={"overrun_ratio": overrun_ratio, "actual": float(actual_total)},
                        fingerprint=fp,
                    )
                )

    return disruptions
