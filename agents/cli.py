"""CLI: Command-line runner for local planning, disruption simulation, and rule validation."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.gateway import (
    resume_replan,
    run_plan,
    run_replan,
)
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.rules.validator_rules import validate_itinerary
from reroute_agents.state import (
    DraftItem,
    InjectedSignals,
    TripSpec,
)


def print_banner(text: str) -> None:
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


async def handle_plan(args: argparse.Namespace) -> None:
    """Handle `plan` CLI command."""
    print_banner(f"Planning Trip: {args.city} ({args.days} days, {args.pace} pace)")

    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places)

    trip_id = uuid4()
    start_d = date.today() + timedelta(days=14)
    end_d = start_d + timedelta(days=args.days - 1)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    spec = TripSpec(
        trip_id=trip_id,
        destination=args.city,
        start_date=start_d,
        end_date=end_d,
        group_size=2,
        budget_total=Decimal(str(args.budget)),
        currency="INR",
        pace=args.pace,
        vibe_tags=tags,
    )
    await repos.trips.save_trip(spec)

    fake_llm = FakeLLM() if args.fake_llm else None
    run_id = uuid4()

    print(f"Run ID: {run_id}")
    print(f"Trip ID: {trip_id}\n")
    print("Streaming agent event timeline:")

    async for event in run_plan(run_id, trip_id, repos=repos, llm_override=fake_llm):
        node_prefix = f"[{event.node.upper()}]" if event.node else "[EVENT]"
        msg = event.message or event.type
        print(f" -> {node_prefix:<18} {msg}")

    curr_v = await repos.itineraries.get_current_version(trip_id)
    if not curr_v:
        print("\nNo itinerary version was created.")
        return

    items = await repos.itineraries.get_version_items(curr_v["id"])
    print_banner(
        f"Final Itinerary Version {curr_v['version_no']} (Total: {curr_v['total_cost']} INR)"
    )
    print(f"Summary: {curr_v['summary']}\n")

    items_by_day: dict[int, list[DraftItem]] = {}
    for it in items:
        items_by_day.setdefault(it.day_index, []).append(it)

    for day in sorted(items_by_day.keys()):
        d_date = start_d + timedelta(days=day - 1)
        print(f"\n--- Day {day} ({d_date.strftime('%A, %b %d')}) ---")
        for it in items_by_day[day]:
            flags_str = f" [Flags: {', '.join(it.flags)}]" if it.flags else ""
            notes_str = f" | Notes: {it.notes}" if it.notes else ""
            print(
                f"  {it.start_time.strftime('%H:%M')} - {it.end_time.strftime('%H:%M')} | "
                f"{it.title:<35} | {it.category:<12} | {it.est_cost:>5} INR{flags_str}{notes_str}"
            )


async def handle_simulate(args: argparse.Namespace) -> None:
    """Handle `simulate` CLI command."""
    print_banner(f"Simulating Disruption: {args.type} on Day {args.day}")

    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places)
    fake_llm = FakeLLM() if args.fake_llm else None

    trip_id = UUID(args.trip) if args.trip else uuid4()
    spec = await repos.trips.get_trip(trip_id)

    # If trip does not exist in memory, generate initial trip first
    if not spec:
        print("Trip not in memory. Generating baseline itinerary first...")
        spec = TripSpec(
            trip_id=trip_id,
            destination="Darjeeling",
            start_date=date(2026, 12, 12),
            end_date=date(2026, 12, 14),
            group_size=2,
            budget_total=Decimal(15000),
            currency="INR",
            pace="balanced",
            vibe_tags=["nature", "food"],
        )
        await repos.trips.save_trip(spec)

        # Baseline plan
        async for _ in run_plan(uuid4(), trip_id, repos=repos, llm_override=fake_llm):
            pass

    curr_v = await repos.itineraries.get_current_version(trip_id)
    if not curr_v:
        print("Failed to prepare base trip.")
        return

    print(f"Base Version: v{curr_v['version_no']}")

    # Prepare injected disruption
    params: dict[str, Any] = {}
    if args.type == "weather":
        params = {"precip_prob": 0.9, "from": "13:00", "to": "17:00"}
    elif args.type == "delay":
        params = {"delay_minutes": 45}
    elif args.type == "budget_overrun":
        params = {"overrun_pct": 0.20}
    elif args.type == "closure":
        params = {"reason": "Landslide on mountain pass"}

    injected = InjectedSignals(
        type=args.type,
        day_index=args.day,
        params=params,
    )

    replan_run_id = uuid4()
    fake_llm = FakeLLM() if args.fake_llm else None

    print("\nRunning Replan Graph...")
    async for event in run_replan(
        replan_run_id,
        trip_id,
        injected=injected,
        repos=repos,
        llm_override=fake_llm,
    ):
        node_prefix = f"[{event.node.upper()}]" if event.node else "[EVENT]"
        msg = event.message or event.type
        print(f" -> {node_prefix:<18} {msg}")

    # Inspect proposal
    proposals = await repos.proposals.get_pending_proposals(trip_id)
    if not proposals:
        print("\nNo proposal was generated (no disruption impact detected).")
        return

    prop = proposals[0]
    print_banner(f"Proposal Pending Review (ID: {prop.id})")
    print(f"Reason: {prop.reason}")
    print(f"Explanation: {prop.explanation}")
    print(f"Impact: Cost delta: {prop.cost_delta} INR, Changes: {prop.items_changed}\n")
    print("Diff:")
    for d in prop.diff:
        b_title = d.before.get("title") if d.before else "(none)"
        a_title = d.after.get("title") if d.after else "(none)"
        print(f"  [{d.op.upper()}] Day {d.day} | {b_title} --> {a_title} | Reason: {d.why}")

    # Terminal HITL Decision
    print("\nDecision Options: [approve / reject / alternatives]")
    choice = input("Enter decision (default: approve): ").strip().lower()
    if choice not in ("approve", "reject", "alternatives"):
        choice = "approve"

    print(f"\nResuming replan with decision: '{choice}'...")
    async for event in resume_replan(
        replan_run_id,
        decision=choice,  # type: ignore[arg-type]
        repos=repos,
        llm_override=fake_llm,
    ):
        node_prefix = f"[{event.node.upper()}]" if event.node else "[EVENT]"
        msg = event.message or event.type
        print(f" -> {node_prefix:<18} {msg}")

    final_v = await repos.itineraries.get_current_version(trip_id)
    if final_v:
        print(f"\nTrip is now at Version: v{final_v['version_no']} (Reason: {final_v['reason']})")


async def handle_check_rules(args: argparse.Namespace) -> None:
    """Handle `check-rules` CLI command."""
    print_banner(f"Validating Rules for: {args.file}")
    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)

    spec_data = data.get("spec", {})
    spec = TripSpec(
        trip_id=UUID(spec_data.get("trip_id", str(uuid4()))),
        destination=spec_data.get("destination", "Darjeeling"),
        start_date=date.fromisoformat(spec_data.get("start_date", "2026-12-12")),
        end_date=date.fromisoformat(spec_data.get("end_date", "2026-12-14")),
        budget_total=Decimal(str(spec_data.get("budget_total", 15000))),
        pace=spec_data.get("pace", "balanced"),
    )

    items = [DraftItem.model_validate(it) for it in data.get("items", [])]
    violations = validate_itinerary(items, spec)

    if not violations:
        print("All deterministic rules passed! No violations found.")
    else:
        print(f"Found {len(violations)} rule violations:\n")
        for v in violations:
            day_str = f"Day {v.day_index}" if v.day_index else "Trip"
            print(f"  [{v.code.upper():<15}] {day_str:<8} | {v.detail}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reroute Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # plan command
    p_plan = subparsers.add_parser("plan", help="Generate an itinerary")
    p_plan.add_argument("--city", default="Darjeeling", help="Destination city name")
    p_plan.add_argument("--days", type=int, default=3, help="Duration in days")
    p_plan.add_argument("--budget", type=float, default=15000.0, help="Total budget in INR")
    p_plan.add_argument("--pace", choices=["relaxed", "balanced", "packed"], default="balanced")
    p_plan.add_argument("--tags", default="food,nature", help="Comma-separated vibe tags")
    p_plan.add_argument("--fake-llm", action="store_true", help="Run with deterministic FakeLLM")
    p_plan.add_argument("--mock-tools", action="store_true", help="Run with mock tools")

    # simulate command
    p_sim = subparsers.add_parser("simulate", help="Simulate a real-world disruption")
    p_sim.add_argument("--trip", help="Optional trip UUID")
    p_sim.add_argument(
        "--type", choices=["weather", "closure", "delay", "budget_overrun"], default="weather"
    )
    p_sim.add_argument("--day", type=int, default=2, help="Day index for disruption")
    p_sim.add_argument("--fake-llm", action="store_true", help="Run with deterministic FakeLLM")
    p_sim.add_argument("--mock-tools", action="store_true", help="Run with mock tools")

    # check-rules command
    p_chk = subparsers.add_parser("check-rules", help="Run validator on JSON itinerary")
    p_chk.add_argument("--file", required=True, help="Path to JSON file")

    # serve command
    p_srv = subparsers.add_parser("serve", help="Run the FastAPI Agent HTTP & SSE server")
    p_srv.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    p_srv.add_argument("--port", type=int, default=8000, help="Port to listen on")
    p_srv.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    if args.command == "plan":
        asyncio.run(handle_plan(args))
    elif args.command == "simulate":
        asyncio.run(handle_simulate(args))
    elif args.command == "check-rules":
        asyncio.run(handle_check_rules(args))
    elif args.command == "serve":
        import uvicorn

        print_banner(f"Starting Reroute Agent API on http://{args.host}:{args.port}")
        uvicorn.run("reroute_agents.api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
