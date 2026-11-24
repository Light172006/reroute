import asyncio
from datetime import date
from decimal import Decimal
from uuid import uuid4

from reroute_agents.config import settings
from reroute_agents.gateway import run_plan
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import TripSpec

async def test_live_planning():
    print("=== Configuration ===")
    print("search_provider:", settings.search_provider)
    print("mock_llm:", settings.mock_llm)
    print("mock_tools:", settings.mock_tools)
    print("llm_strong_chain:", settings.llm_strong_chain)

    repos = create_in_memory_repositories()
    trip_id = uuid4()
    run_id = uuid4()

    spec = TripSpec(
        trip_id=trip_id,
        destination="Goa",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 11),
        group_size=2,
        budget_total=Decimal("20000"),
        currency="INR",
        pace="balanced",
        vibe_tags=["beaches", "heritage"],
    )
    await repos.trips.save_trip(spec)

    print("\n=== Executing Live Plan Graph for Goa ===")
    events = []
    async for evt in run_plan(run_id, trip_id, repos=repos):
        events.append(evt)
        summary = evt.payload.get("message") or evt.payload.get("summary") or evt.payload.get("text") or ""
        print(f"[{evt.type}] {summary}")

    curr_v = await repos.itineraries.get_current_version(trip_id)
    print("\n=== Final Verified Version ===")
    print("Version info:", curr_v)
    if curr_v:
        items = await repos.itineraries.get_version_items(curr_v["id"])
        print(f"Total scheduled stops: {len(items)}")
        for it in items:
            title = it.title if hasattr(it, "title") else it["title"]
            day = it.day_index if hasattr(it, "day_index") else it["day_index"]
            start = it.start_time if hasattr(it, "start_time") else it["start_time"]
            end = it.end_time if hasattr(it, "end_time") else it["end_time"]
            cost = it.est_cost if hasattr(it, "est_cost") else it["est_cost"]
            print(f"  Day {day} [{start} - {end}] {title} (Cost: {cost})")

if __name__ == "__main__":
    asyncio.run(test_live_planning())
