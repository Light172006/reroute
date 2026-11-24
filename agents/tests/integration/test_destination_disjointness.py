"""Regression test for destination disjointness and bounding box compliance.

Ensures that choosing different destinations (e.g. Arunachal Pradesh vs Sikkim,
or Tawang vs Gangtok) returns destination-specific places within the appropriate
geographical bounds, rather than falling back to identical or Darjeeling-based places.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.gateway import run_plan
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import TripSpec


# Geographic bounding boxes [min_lat, min_lng, max_lat, max_lng]
BOUNDING_BOXES = {
    "arunachal": {"min_lat": 26.5, "max_lat": 29.5, "min_lng": 91.5, "max_lng": 97.5},
    "sikkim": {"min_lat": 27.0, "max_lat": 28.2, "min_lng": 88.0, "max_lng": 89.0},
    "darjeeling": {"min_lat": 26.9, "max_lat": 27.2, "min_lng": 88.1, "max_lng": 88.4},
}


@pytest.mark.asyncio
async def test_destination_disjointness_arunachal_vs_sikkim() -> None:
    """Verify planning for Arunachal Pradesh and Sikkim returns disjoint place sets."""
    repos = create_in_memory_repositories()
    # Load all available seed catalogs
    await load_seed_catalog_into_repository(repos.places, "arunachal")
    await load_seed_catalog_into_repository(repos.places, "sikkim")
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    # Plan 1: Arunachal Pradesh
    trip_id_arunachal = uuid4()
    spec_arunachal = TripSpec(
        trip_id=trip_id_arunachal,
        destination="Arunachal Pradesh",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 3),
        group_size=2,
        budget_total=Decimal(25000),
        currency="INR",
        pace="balanced",
    )
    await repos.trips.save_trip(spec_arunachal)

    async for _ in run_plan(uuid4(), trip_id_arunachal, repos=repos, llm_override=FakeLLM()):
        pass

    it_arunachal = await repos.itineraries.get_current_version(trip_id_arunachal)
    assert it_arunachal is not None
    items_arunachal = await repos.itineraries.get_version_items(it_arunachal["id"])
    arunachal_places = [item.title for item in items_arunachal]

    # Plan 2: Sikkim
    trip_id_sikkim = uuid4()
    spec_sikkim = TripSpec(
        trip_id=trip_id_sikkim,
        destination="Sikkim",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 3),
        group_size=2,
        budget_total=Decimal(25000),
        currency="INR",
        pace="balanced",
    )
    await repos.trips.save_trip(spec_sikkim)

    async for _ in run_plan(uuid4(), trip_id_sikkim, repos=repos, llm_override=FakeLLM()):
        pass

    it_sikkim = await repos.itineraries.get_current_version(trip_id_sikkim)
    assert it_sikkim is not None
    items_sikkim = await repos.itineraries.get_version_items(it_sikkim["id"])
    sikkim_places = [item.title for item in items_sikkim]

    # Assert places are returned for both destinations
    assert len(arunachal_places) > 0, "Expected places for Arunachal Pradesh itinerary"
    assert len(sikkim_places) > 0, "Expected places for Sikkim itinerary"

    # CRITICAL: Destination disjointness check
    intersection = set(arunachal_places).intersection(set(sikkim_places))
    assert not intersection, (
        f"Expected Arunachal and Sikkim itineraries to be disjoint, but found overlapping places: {intersection}"
    )

    # Check that place coordinates fall within region bounding boxes
    bbox_arunachal = BOUNDING_BOXES["arunachal"]
    for item in items_arunachal:
        assert (
            bbox_arunachal["min_lat"] <= item.lat <= bbox_arunachal["max_lat"]
            and bbox_arunachal["min_lng"] <= item.lng <= bbox_arunachal["max_lng"]
        ), f"Arunachal place '{item.title}' at ({item.lat}, {item.lng}) outside bounding box"

    bbox_sikkim = BOUNDING_BOXES["sikkim"]
    for item in items_sikkim:
        assert (
            bbox_sikkim["min_lat"] <= item.lat <= bbox_sikkim["max_lat"]
            and bbox_sikkim["min_lng"] <= item.lng <= bbox_sikkim["max_lng"]
        ), f"Sikkim place '{item.title}' at ({item.lat}, {item.lng}) outside bounding box"


@pytest.mark.asyncio
async def test_subregion_destination_not_defaulting_to_darjeeling() -> None:
    """Verify sub-region/town destinations like Tawang do not default to Darjeeling."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "arunachal")
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    trip_id = uuid4()
    spec = TripSpec(
        trip_id=trip_id,
        destination="Tawang",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        group_size=2,
        budget_total=Decimal(15000),
        currency="INR",
        pace="balanced",
    )
    await repos.trips.save_trip(spec)

    async for _ in run_plan(uuid4(), trip_id, repos=repos, llm_override=FakeLLM()):
        pass

    it = await repos.itineraries.get_current_version(trip_id)
    assert it is not None
    items = await repos.itineraries.get_version_items(it["id"])

    # Tawang coordinates must NOT be Darjeeling (27.04, 88.26)
    darjeeling_lat, darjeeling_lng = 27.04, 88.26
    for item in items:
        assert not (item.lat == darjeeling_lat and item.lng == darjeeling_lng), (
            f"Item '{item.title}' defaulted to Darjeeling coordinates ({item.lat}, {item.lng})"
        )
