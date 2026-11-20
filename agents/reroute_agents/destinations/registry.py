"""Destination registry and seed catalog repository loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid5

from reroute_agents.repositories.interfaces import PlaceCatalogRepository
from reroute_agents.state import PlaceCandidate

# Stable namespace for generating deterministic UUIDs from seed external_ids
SEED_UUID_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@dataclass(frozen=True)
class DestinationConfig:
    id: str
    display_name: str
    seed_filename: str
    gateway_city: str | None
    min_altitude_m: int
    max_altitude_m: int
    aliases: tuple[str, ...]


DESTINATIONS_REGISTRY: dict[str, DestinationConfig] = {
    "darjeeling": DestinationConfig(
        id="darjeeling",
        display_name="Darjeeling & Surroundings",
        seed_filename="darjeeling.json",
        gateway_city="Siliguri",
        min_altitude_m=1400,
        max_altitude_m=2600,
        aliases=("darjeeling", "kalimpong", "mirik", "ghum"),
    ),
    "north_sikkim": DestinationConfig(
        id="north_sikkim",
        display_name="North Sikkim & Gangtok",
        seed_filename="north_sikkim.json",
        gateway_city="Gangtok",
        min_altitude_m=1500,
        max_altitude_m=5200,
        aliases=("north sikkim", "sikkim", "gangtok", "lachen", "lachung", "yumthang"),
    ),
    "arunachal": DestinationConfig(
        id="arunachal",
        display_name="Arunachal Pradesh (Tawang & Ziro)",
        seed_filename="arunachal.json",
        gateway_city="Guwahati",
        min_altitude_m=1500,
        max_altitude_m=4200,
        aliases=("arunachal", "arunachal pradesh", "tawang", "dirang", "bomdila", "ziro"),
    ),
    "ladakh": DestinationConfig(
        id="ladakh",
        display_name="Ladakh (Leh, Nubra & Pangong)",
        seed_filename="ladakh.json",
        gateway_city="Leh",
        min_altitude_m=3100,
        max_altitude_m=5400,
        aliases=("ladakh", "leh", "nubra", "nubra valley", "pangong", "pangong tso"),
    ),
}


def resolve_destination(query: str) -> DestinationConfig | None:
    """Find destination configuration matching query or alias."""
    q_norm = query.lower().strip()
    if q_norm in DESTINATIONS_REGISTRY:
        return DESTINATIONS_REGISTRY[q_norm]

    for cfg in DESTINATIONS_REGISTRY.values():
        if q_norm == cfg.display_name.lower():
            return cfg
        if any(alias in q_norm or q_norm in alias for alias in cfg.aliases):
            return cfg

    return None


def get_seed_dir() -> Path:
    """Return path to data/seed directory."""
    return Path(__file__).resolve().parent.parent.parent / "data" / "seed"


async def load_seed_catalog_into_repository(
    repo: PlaceCatalogRepository,
    destination_id: str | None = None,
) -> int:
    """Load and upsert seed JSON places into the provided repository."""
    seed_dir = get_seed_dir()
    configs_to_load = (
        [DESTINATIONS_REGISTRY[destination_id]]
        if destination_id and destination_id in DESTINATIONS_REGISTRY
        else list(DESTINATIONS_REGISTRY.values())
    )

    loaded_count = 0
    for cfg in configs_to_load:
        file_path = seed_dir / cfg.seed_filename
        if not file_path.exists():
            continue

        with open(file_path, encoding="utf-8") as f:
            raw_places = json.load(f)

        for item in raw_places:
            ext_id = item.get("external_id", f"seed:{cfg.id}:{item['name']}")
            place_uuid = uuid5(SEED_UUID_NAMESPACE, ext_id)
            candidate = PlaceCandidate(
                id=place_uuid,
                external_id=ext_id,
                name=item["name"],
                city=item.get("city", cfg.display_name),
                country=item.get("country", "IN"),
                category=item["category"],
                setting=item.get("setting", "mixed"),
                avg_cost=Decimal(str(item.get("avg_cost", 0))),
                currency=item.get("currency", "INR"),
                avg_duration_min=item.get("avg_duration_min", 60),
                opening_hours=item.get("opening_hours"),
                hours_confidence=item.get("hours_confidence", "unknown"),
                lat=item["lat"],
                lng=item["lng"],
                rating=item.get("rating"),
                tags=item.get("tags", []),
                description=item.get("description"),
                raw=item.get("raw", {}),
            )
            await repo.upsert_place(candidate)
            loaded_count += 1

    return loaded_count
