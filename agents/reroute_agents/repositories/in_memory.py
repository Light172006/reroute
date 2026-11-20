"""In-memory repository implementations for testing and standalone CLI execution."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from reroute_agents.repositories.interfaces import (
    CacheRepository,
    DisruptionRepository,
    ExpenseRepository,
    ItineraryRepository,
    PlaceCatalogRepository,
    ProposalRepository,
    RepositoriesBundle,
    RunEventRepository,
    TripRepository,
)
from reroute_agents.state import (
    AgentEvent,
    DisruptionEvent,
    DraftItem,
    PlaceCandidate,
    ReplanProposal,
    TripSpec,
)


class InMemoryTripRepository(TripRepository):
    def __init__(self) -> None:
        self.trips: dict[UUID, TripSpec] = {}
        self.current_versions: dict[UUID, UUID] = {}
        self._lock = asyncio.Lock()

    async def get_trip(self, trip_id: UUID) -> TripSpec | None:
        async with self._lock:
            return self.trips.get(trip_id)

    async def save_trip(self, trip: TripSpec) -> None:
        async with self._lock:
            self.trips[trip.trip_id] = trip

    async def update_current_version(self, trip_id: UUID, version_id: UUID) -> None:
        async with self._lock:
            self.current_versions[trip_id] = version_id


class InMemoryItineraryRepository(ItineraryRepository):
    def __init__(self) -> None:
        self.versions: dict[UUID, dict[str, Any]] = {}
        self.version_items: dict[UUID, list[DraftItem]] = {}
        self.trip_versions: dict[UUID, list[UUID]] = {}
        self._lock = asyncio.Lock()

    async def get_current_version(self, trip_id: UUID) -> dict[str, Any] | None:
        async with self._lock:
            v_ids = self.trip_versions.get(trip_id, [])
            if not v_ids:
                return None
            latest_id = v_ids[-1]
            return self.versions.get(latest_id)

    async def get_version_items(self, version_id: UUID) -> list[DraftItem]:
        async with self._lock:
            # Return deep copy of items
            items = self.version_items.get(version_id, [])
            return [item.model_copy(deep=True) for item in items]

    async def save_version(
        self,
        trip_id: UUID,
        version_no: int,
        reason: str,
        created_by: str,
        items: list[DraftItem],
        parent_version_id: UUID | None = None,
        proposal_id: UUID | None = None,
        run_id: UUID | None = None,
        summary: str = "",
    ) -> UUID:
        async with self._lock:
            v_id = uuid4()
            total_cost = sum((item.est_cost for item in items), Decimal(0))
            record = {
                "id": v_id,
                "trip_id": trip_id,
                "version_no": version_no,
                "parent_version_id": parent_version_id,
                "reason": reason,
                "created_by": created_by,
                "proposal_id": proposal_id,
                "run_id": run_id,
                "total_cost": total_cost,
                "summary": summary,
                "created_at": datetime.now(UTC),
            }
            self.versions[v_id] = record
            self.version_items[v_id] = [item.model_copy(deep=True) for item in items]
            if trip_id not in self.trip_versions:
                self.trip_versions[trip_id] = []
            self.trip_versions[trip_id].append(v_id)
            return v_id

    async def get_version_by_id(self, version_id: UUID) -> dict[str, Any] | None:
        async with self._lock:
            return self.versions.get(version_id)


class InMemoryProposalRepository(ProposalRepository):
    def __init__(self) -> None:
        self.proposals: dict[UUID, ReplanProposal] = {}
        self._lock = asyncio.Lock()

    async def save_proposal(self, proposal: ReplanProposal) -> None:
        async with self._lock:
            self.proposals[proposal.id] = proposal.model_copy(deep=True)

    async def get_proposal(self, proposal_id: UUID) -> ReplanProposal | None:
        async with self._lock:
            p = self.proposals.get(proposal_id)
            return p.model_copy(deep=True) if p else None

    async def update_proposal_status(
        self,
        proposal_id: UUID,
        status: str,
        resulting_version_id: UUID | None = None,
        note: str | None = None,
    ) -> None:
        async with self._lock:
            if proposal_id in self.proposals:
                proposal = self.proposals[proposal_id]
                proposal.status = status  # type: ignore[assignment]
                if resulting_version_id:
                    proposal.resulting_version_id = resulting_version_id

    async def get_pending_proposals(self, trip_id: UUID) -> list[ReplanProposal]:
        async with self._lock:
            return [
                p.model_copy(deep=True)
                for p in self.proposals.values()
                if p.trip_id == trip_id and p.status == "pending"
            ]


class InMemoryDisruptionRepository(DisruptionRepository):
    def __init__(self) -> None:
        self.disruptions: dict[UUID, DisruptionEvent] = {}
        self._lock = asyncio.Lock()

    async def save_disruption(self, disruption: DisruptionEvent) -> None:
        async with self._lock:
            self.disruptions[disruption.id] = disruption.model_copy(deep=True)

    async def get_disruption_by_fingerprint(
        self, trip_id: UUID, fingerprint: str
    ) -> DisruptionEvent | None:
        async with self._lock:
            for d in self.disruptions.values():
                if d.trip_id == trip_id and d.fingerprint == fingerprint:
                    return d.model_copy(deep=True)
            return None

    async def get_active_disruptions(self, trip_id: UUID) -> list[DisruptionEvent]:
        async with self._lock:
            return [
                d.model_copy(deep=True) for d in self.disruptions.values() if d.trip_id == trip_id
            ]

    async def resolve_disruption(self, disruption_id: UUID) -> None:
        async with self._lock:
            self.disruptions.pop(disruption_id, None)


class InMemoryPlaceCatalogRepository(PlaceCatalogRepository):
    def __init__(self) -> None:
        self.places: dict[UUID, PlaceCandidate] = {}
        self._lock = asyncio.Lock()

    async def search_places(
        self,
        city: str,
        query: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 30,
    ) -> list[PlaceCandidate]:
        async with self._lock:
            matches: list[PlaceCandidate] = []
            city_lower = city.lower().strip()
            for p in self.places.values():
                p_city_lower = p.city.lower()
                # Check city match in either direction
                if city_lower not in p_city_lower and p_city_lower not in city_lower:
                    continue
                if category and p.category.lower() != category.lower():
                    continue
                if query:
                    q_lower = query.lower()
                    if q_lower not in p.name.lower() and (
                        not p.description or q_lower not in p.description.lower()
                    ):
                        continue
                if tags:
                    tag_set = {t.lower() for t in p.tags}
                    if not any(req_tag.lower() in tag_set for req_tag in tags):
                        continue
                matches.append(p.model_copy(deep=True))
                if len(matches) >= limit:
                    break
            # Fallback: if category or tag filter yielded too few, search without tag filter
            if len(matches) < 5:
                for p in self.places.values():
                    if city_lower in p.city.lower() and p not in matches:
                        matches.append(p.model_copy(deep=True))
                        if len(matches) >= limit:
                            break
            return matches

    async def get_place_by_id(self, place_id: UUID) -> PlaceCandidate | None:
        async with self._lock:
            p = self.places.get(place_id)
            return p.model_copy(deep=True) if p else None

    async def upsert_place(self, place: PlaceCandidate) -> None:
        async with self._lock:
            self.places[place.id] = place.model_copy(deep=True)


class InMemoryExpenseRepository(ExpenseRepository):
    def __init__(self) -> None:
        self.expenses: dict[UUID, list[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def get_expenses(self, trip_id: UUID) -> list[dict[str, Any]]:
        async with self._lock:
            return list(self.expenses.get(trip_id, []))

    async def get_expenses_summary(self, trip_id: UUID) -> dict[str, Any]:
        async with self._lock:
            expenses = self.expenses.get(trip_id, [])
            total = sum((Decimal(str(e["amount"])) for e in expenses), Decimal(0))
            by_category: dict[str, Decimal] = {}
            for e in expenses:
                cat = e["category"]
                by_category[cat] = by_category.get(cat, Decimal(0)) + Decimal(str(e["amount"]))
            return {
                "total": total,
                "by_category": {k: float(v) for k, v in by_category.items()},
                "count": len(expenses),
            }

    async def add_expense(
        self,
        trip_id: UUID,
        category: str,
        amount: Decimal,
        currency: str = "INR",
        description: str | None = None,
        item_stable_key: UUID | None = None,
    ) -> UUID:
        async with self._lock:
            e_id = uuid4()
            item = {
                "id": e_id,
                "trip_id": trip_id,
                "category": category,
                "amount": amount,
                "currency": currency,
                "description": description,
                "item_stable_key": item_stable_key,
                "spent_at": datetime.now(UTC),
            }
            if trip_id not in self.expenses:
                self.expenses[trip_id] = []
            self.expenses[trip_id].append(item)
            return e_id


class InMemoryCacheRepository(CacheRepository):
    def __init__(self) -> None:
        self.cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> dict[str, Any] | None:
        async with self._lock:
            entry = self.cache.get(key)
            if not entry:
                return None
            if entry["expires_at"] < datetime.now(UTC):
                del self.cache[key]
                return None
            return entry["data"]

    async def set(
        self, key: str, provider: str, data: dict[str, Any], ttl_seconds: int = 3600
    ) -> None:
        async with self._lock:
            expires_at = datetime.fromtimestamp(datetime.now(UTC).timestamp() + ttl_seconds)
            self.cache[key] = {
                "provider": provider,
                "data": data,
                "expires_at": expires_at,
            }


class InMemoryRunEventRepository(RunEventRepository):
    def __init__(self) -> None:
        self.events: dict[UUID, list[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def log_event(self, run_id: UUID, event: AgentEvent) -> int:
        async with self._lock:
            if run_id not in self.events:
                self.events[run_id] = []
            seq = len(self.events[run_id]) + 1
            record = {
                "seq": seq,
                "type": event.type,
                "node": event.node,
                "message": event.message,
                "status": event.status,
                "payload": event.payload,
                "created_at": datetime.now(UTC),
            }
            self.events[run_id].append(record)
            return seq

    async def get_events(self, run_id: UUID, after_seq: int = 0) -> list[dict[str, Any]]:
        async with self._lock:
            all_events = self.events.get(run_id, [])
            return [e for e in all_events if e["seq"] > after_seq]


def create_in_memory_repositories() -> RepositoriesBundle:
    return RepositoriesBundle(
        trips=InMemoryTripRepository(),
        itineraries=InMemoryItineraryRepository(),
        proposals=InMemoryProposalRepository(),
        disruptions=InMemoryDisruptionRepository(),
        places=InMemoryPlaceCatalogRepository(),
        expenses=InMemoryExpenseRepository(),
        cache=InMemoryCacheRepository(),
        run_events=InMemoryRunEventRepository(),
    )
