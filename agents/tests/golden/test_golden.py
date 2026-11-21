"""Characterization snapshot generator and regression test for golden outputs."""

from __future__ import annotations

import asyncio
from datetime import date, time as dtime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.evaluation.run_eval import run_evaluation_benchmark
from reroute_agents.gateway import resume_replan, run_chat, run_plan, run_replan
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import (
    AgentEvent,
    DraftItem,
    InjectedSignals,
    ItineraryDraft,
    TripSpec,
)

GOLDEN_FILE = Path(__file__).resolve().parent / "golden_data.json"
REGIONS = ["darjeeling", "north_sikkim", "arunachal", "ladakh"]


def _sanitize_event(evt: AgentEvent) -> dict[str, Any]:
    dump = evt.model_dump(mode="json")
    payload = dump.get("payload", {})
    # Sanitize dynamic IDs
    sanitized_payload = {}
    for k, v in payload.items():
        if "id" in k.lower() or "run" in k.lower():
            sanitized_payload[k] = "<ID>"
        elif isinstance(v, (int, float, str, bool, list, dict)):
            sanitized_payload[k] = v
        else:
            sanitized_payload[k] = str(v)

    return {
        "type": dump.get("type"),
        "node": dump.get("node"),
        "status": dump.get("status"),
        "message": dump.get("message"),
        "payload_keys": sorted(payload.keys()),
    }


def _make_region_draft(region: str) -> ItineraryDraft:
    return ItineraryDraft(
        items=[
            DraftItem(
                day_index=1,
                position=0,
                place_id=UUID(int=101),
                title=f"{region.title()} Morning Stop",
                category="culture",
                setting="indoor",
                start_time=dtime(9, 30),
                end_time=dtime(11, 30),
                est_cost=Decimal(100),
            ),
            DraftItem(
                day_index=2,
                position=0,
                place_id=UUID(int=102),
                title=f"{region.title()} Outdoor Trek",
                category="nature",
                setting="outdoor",
                start_time=dtime(14, 0),
                end_time=dtime(16, 0),
                est_cost=Decimal(200),
            ),
        ],
        summary=f"{region.title()} 2-day draft",
    )


async def generate_snapshots() -> dict[str, Any]:
    golden: dict[str, Any] = {"regions": {}, "eval_metrics": {}}

    for idx, region in enumerate(REGIONS, start=1):
        repos = create_in_memory_repositories()
        await load_seed_catalog_into_repository(repos.places, region)

        trip_id = UUID(int=idx * 1000)
        spec = TripSpec(
            trip_id=trip_id,
            destination=region.replace("_", " ").title(),
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 2),
            budget_total=Decimal(15000),
            currency="INR",
            pace="balanced",
            vibe_tags=["culture", "nature"],
        )
        await repos.trips.save_trip(spec)

        fake_llm = FakeLLM(canned_responses={"ItineraryDraft": _make_region_draft(region)})

        # 1. Plan run
        plan_run_id = UUID(int=idx * 1000 + 1)
        plan_events = []
        with patch("reroute_agents.tools.weather.is_mock_tools", return_value=True):
            async for evt in run_plan(
                run_id=plan_run_id,
                trip_id=trip_id,
                repos=repos,
                llm_override=fake_llm,
            ):
                plan_events.append(_sanitize_event(evt))

        curr_v = await repos.itineraries.get_current_version(trip_id)
        assert curr_v is not None
        plan_items = await repos.itineraries.get_version_items(curr_v["id"])
        item_summaries = [
            {"day": it.day_index, "title": it.title, "cost": float(it.est_cost)}
            for it in plan_items
        ]

        # 2. Replan run
        replan_run_id = UUID(int=idx * 1000 + 2)
        injected = InjectedSignals(
            type="weather",
            day_index=2,
            params={"precip_prob": 0.95, "from": "14:00", "to": "16:00"},
        )
        replan_events = []
        with patch("reroute_agents.tools.weather.is_mock_tools", return_value=True):
            async for evt in run_replan(
                run_id=replan_run_id,
                trip_id=trip_id,
                injected=injected,
                repos=repos,
                llm_override=fake_llm,
            ):
                replan_events.append(_sanitize_event(evt))

            # Resume and approve
            resume_events = []
            async for evt in resume_replan(
                run_id=replan_run_id,
                decision="approve",
                repos=repos,
                llm_override=fake_llm,
            ):
                resume_events.append(_sanitize_event(evt))

        # 3. Chat run
        chat_run_id = UUID(int=idx * 1000 + 3)
        chat_events = []
        with patch("reroute_agents.tools.weather.is_mock_tools", return_value=True):
            async for evt in run_chat(
                run_id=chat_run_id,
                trip_id=trip_id,
                message="What should I pack for this trip?",
                repos=repos,
                llm_override=fake_llm,
            ):
                chat_events.append(_sanitize_event(evt))

        golden["regions"][region] = {
            "plan_events": plan_events,
            "plan_items": item_summaries,
            "replan_events": replan_events,
            "resume_events": resume_events,
            "chat_events": chat_events,
        }

    # 4. Evaluation benchmark metrics
    eval_res = await run_evaluation_benchmark()
    golden["eval_metrics"] = {
        "success_rate": eval_res.get("success_rate"),
        "constraint_rate": eval_res.get("constraint_rate"),
        "purity_rate": eval_res.get("purity_rate"),
    }

    return golden


@pytest.mark.asyncio
async def test_characterization_golden_snapshot() -> None:
    """Verify that current system matches golden characterization snapshot."""
    assert GOLDEN_FILE.exists(), "Golden snapshot file missing"
    with open(GOLDEN_FILE, encoding="utf-8") as f:
        golden_expected = json.load(f)

    golden_actual = await generate_snapshots()

    # Compare metrics
    assert golden_actual["eval_metrics"] == golden_expected["eval_metrics"]

    # Compare region events and outputs
    for region in REGIONS:
        exp = golden_expected["regions"][region]
        act = golden_actual["regions"][region]

        assert len(act["plan_events"]) == len(exp["plan_events"])
        for e_act, e_exp in zip(act["plan_events"], exp["plan_events"]):
            assert e_act["type"] == e_exp["type"]
            assert e_act["node"] == e_exp["node"]
            assert e_act["status"] == e_exp["status"]

        assert act["plan_items"] == exp["plan_items"]
        assert len(act["replan_events"]) == len(exp["replan_events"])
        assert len(act["chat_events"]) == len(exp["chat_events"])


if __name__ == "__main__":
    data = asyncio.run(generate_snapshots())
    with open(GOLDEN_FILE, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2)
    print("Golden snapshot generated at:", GOLDEN_FILE)
