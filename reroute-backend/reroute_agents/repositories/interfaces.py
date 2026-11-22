"""Repository Protocol interfaces for data access decoupling."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from reroute_agents.state import (
    AgentEvent,
    DisruptionEvent,
    DraftItem,
    PlaceCandidate,
    ReplanProposal,
    TripSpec,
)


@runtime_checkable
class TripRepository(Protocol):
    async def get_trip(self, trip_id: UUID) -> TripSpec | None: ...
    async def save_trip(self, trip: TripSpec) -> None: ...
    async def update_current_version(self, trip_id: UUID, version_id: UUID) -> None: ...


@runtime_checkable
class ItineraryRepository(Protocol):
    async def get_current_version(self, trip_id: UUID) -> dict[str, Any] | None: ...
    async def get_version_items(self, version_id: UUID) -> list[DraftItem]: ...
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
    ) -> UUID: ...
    async def get_version_by_id(self, version_id: UUID) -> dict[str, Any] | None: ...


@runtime_checkable
class ProposalRepository(Protocol):
    async def save_proposal(self, proposal: ReplanProposal) -> None: ...
    async def get_proposal(self, proposal_id: UUID) -> ReplanProposal | None: ...
    async def update_proposal_status(
        self,
        proposal_id: UUID,
        status: str,
        resulting_version_id: UUID | None = None,
        note: str | None = None,
    ) -> None: ...
    async def get_pending_proposals(self, trip_id: UUID) -> list[ReplanProposal]: ...


@runtime_checkable
class DisruptionRepository(Protocol):
    async def save_disruption(self, disruption: DisruptionEvent) -> None: ...
    async def get_disruption_by_fingerprint(
        self, trip_id: UUID, fingerprint: str
    ) -> DisruptionEvent | None: ...
    async def get_active_disruptions(self, trip_id: UUID) -> list[DisruptionEvent]: ...
    async def resolve_disruption(self, disruption_id: UUID) -> None: ...


@runtime_checkable
class PlaceCatalogRepository(Protocol):
    async def search_places(
        self,
        city: str,
        query: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 30,
    ) -> list[PlaceCandidate]: ...
    async def get_place_by_id(self, place_id: UUID) -> PlaceCandidate | None: ...
    async def upsert_place(self, place: PlaceCandidate) -> None: ...


@runtime_checkable
class ExpenseRepository(Protocol):
    async def get_expenses(self, trip_id: UUID) -> list[dict[str, Any]]: ...
    async def get_expenses_summary(self, trip_id: UUID) -> dict[str, Any]: ...
    async def add_expense(
        self,
        trip_id: UUID,
        category: str,
        amount: Decimal,
        currency: str = "INR",
        description: str | None = None,
        item_stable_key: UUID | None = None,
    ) -> UUID: ...


@runtime_checkable
class CacheRepository(Protocol):
    async def get(self, key: str) -> dict[str, Any] | None: ...
    async def set(
        self, key: str, provider: str, data: dict[str, Any], ttl_seconds: int = 3600
    ) -> None: ...


@runtime_checkable
class RunEventRepository(Protocol):
    async def log_event(self, run_id: UUID, event: AgentEvent) -> int: ...
    async def get_events(self, run_id: UUID, after_seq: int = 0) -> list[dict[str, Any]]: ...


class RepositoriesBundle:
    def __init__(
        self,
        trips: TripRepository,
        itineraries: ItineraryRepository,
        proposals: ProposalRepository,
        disruptions: DisruptionRepository,
        places: PlaceCatalogRepository,
        expenses: ExpenseRepository,
        cache: CacheRepository,
        run_events: RunEventRepository,
    ) -> None:
        self.trips = trips
        self.itineraries = itineraries
        self.proposals = proposals
        self.disruptions = disruptions
        self.places = places
        self.expenses = expenses
        self.cache = cache
        self.run_events = run_events
