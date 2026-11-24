"""SQLAlchemy implementations of the reroute_agents repository protocols.

This module bridges the backend's SQLAlchemy models with the agent package's
Protocol interfaces, enabling the agent runtime to persist state without
direct database knowledge.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from reroute_agents.repositories.interfaces import (
    CacheRepository,
    DisruptionRepository,
    ExpenseRepository,
    ItineraryRepository,
    PlaceCatalogRepository,
    ProposalRepository,
    RunEventRepository,
    TripRepository,
)
from reroute_agents.state import (
    AgentEvent,
    DisruptionEvent,
    DraftItem,
    InjectedSignals,
    PlaceCandidate,
    ReplanProposal,
    TripSpec,
)

from app.db.models import (
    AgentRunEvent,
    DisruptionEvent as DisruptionModel,
    ItineraryItem,
    ItineraryVersion,
    ReplanProposal as ProposalModel,
    Trip,
)


class SQLAlchemyTripRepository(TripRepository):
    """SQLAlchemy adapter for TripRepository protocol."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_trip(self, trip_id: UUID) -> TripSpec | None:
        trip = await self.db.get(Trip, trip_id)
        if not trip:
            return None
        # Handle both datetime and date objects
        def to_date(dt):
            if dt is None:
                return None
            if hasattr(dt, 'date'):
                return dt.date()
            return dt  # already a date
        return TripSpec(
            trip_id=trip.id,
            destination=trip.destination,
            start_date=to_date(trip.start_date),
            end_date=to_date(trip.end_date),
            group_size=trip.group_size or 1,
            budget_total=Decimal(str(trip.budget_total or 0)),
            currency=trip.currency or "INR",
            pace=trip.pace.value if trip.pace else "balanced",
            vibe_tags=trip.vibe_tags or [],
            notes=trip.notes,
            budget_per_day_cap=Decimal(str(trip.budget_per_day_cap)) if trip.budget_per_day_cap else None,
        )

    async def save_trip(self, trip: TripSpec) -> None:
        db_trip = await self.db.get(Trip, trip.trip_id)
        if not db_trip:
            db_trip = Trip(id=trip.trip_id)
            self.db.add(db_trip)

        db_trip.destination = trip.destination
        db_trip.start_date = trip.start_date
        db_trip.end_date = trip.end_date
        db_trip.group_size = trip.group_size
        db_trip.budget_total = trip.budget_total
        db_trip.currency = trip.currency
        db_trip.pace = trip.pace
        db_trip.vibe_tags = trip.vibe_tags
        db_trip.notes = trip.notes
        db_trip.budget_per_day_cap = trip.budget_per_day_cap
        db_trip.status = "draft"
        await self.db.flush()

    async def update_current_version(self, trip_id: UUID, version_id: UUID) -> None:
        trip = await self.db.get(Trip, trip_id)
        if trip:
            trip.current_version_id = version_id
            await self.db.flush()


class SQLAlchemyItineraryRepository(ItineraryRepository):
    """SQLAlchemy adapter for ItineraryRepository protocol."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_current_version(self, trip_id: UUID) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(ItineraryVersion)
            .where(ItineraryVersion.trip_id == trip_id)
            .order_by(ItineraryVersion.version_no.desc())
            .limit(1)
        )
        version = result.scalar_one_or_none()
        if not version:
            return None
        return {
            "id": version.id,
            "trip_id": str(version.trip_id),
            "version_no": version.version_no,
            "reason": version.reason,
            "created_by": version.created_by,
            "proposal_id": str(version.proposal_id) if version.proposal_id else None,
            "run_id": str(version.run_id) if version.run_id else None,
            "total_cost": version.total_cost,
            "summary": version.summary,
            "created_at": version.created_at.isoformat() if version.created_at else None,
        }

    async def get_version_items(self, version_id: UUID) -> list[DraftItem]:
        result = await self.db.execute(
            select(ItineraryItem)
            .where(ItineraryItem.version_id == version_id)
            .order_by(ItineraryItem.day_index, ItineraryItem.position)
        )
        items = result.scalars().all()

        draft_items = []
        for item in items:
            draft_items.append(DraftItem(
                stable_key=item.stable_key,
                day_index=item.day_index,
                position=item.position,
                place_id=item.place_id,
                title=item.title,
                category=item.category.value if item.category else "other",
                setting=item.setting.value if item.setting else "mixed",
                start_time=item.start_time,
                end_time=item.end_time,
                est_cost=item.est_cost or Decimal(0),
                lat=item.lat,
                lng=item.lng,
                is_locked=item.is_locked,
                travel_mode=item.travel_mode.value if item.travel_mode else None,
                travel_minutes=item.travel_minutes,
                travel_distance_m=item.travel_distance_m,
                flags=item.flags or [],
                notes=item.notes,
            ))
        return draft_items

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
        version_id = uuid4()
        total_cost = sum((i.est_cost for i in items), Decimal(0))

        # Create the version row
        version = ItineraryVersion(
            id=version_id,
            trip_id=trip_id,
            version_no=version_no,
            reason=reason,
            created_by=created_by,
            parent_version_id=parent_version_id,
            proposal_id=proposal_id,
            run_id=run_id,
            total_cost=total_cost,
            summary=summary,
        )
        self.db.add(version)

        # Collect all valid place IDs in database to prevent FK constraint violation
        place_ids = [item.place_id for item in items if item.place_id is not None]
        valid_place_ids = set()
        if place_ids:
            from app.db.models import Place
            p_res = await self.db.execute(select(Place.id).where(Place.id.in_(place_ids)))
            valid_place_ids = set(p_res.scalars().all())

        # Create itinerary items
        for item in items:
            actual_place_id = item.place_id if (item.place_id and item.place_id in valid_place_ids) else None
            it_item = ItineraryItem(
                id=uuid4(),  # Item gets its own UUID (stable_key is separate)
                version_id=version_id,
                stable_key=item.stable_key,
                day_index=item.day_index,
                position=item.position,
                place_id=actual_place_id,
                title=item.title,
                category=item.category,
                setting=item.setting,
                start_time=item.start_time,
                end_time=item.end_time,
                est_cost=item.est_cost,
                lat=item.lat,
                lng=item.lng,
                is_locked=item.is_locked,
                travel_mode=item.travel_mode,
                travel_minutes=item.travel_minutes,
                travel_distance_m=item.travel_distance_m,
                flags=item.flags,
                notes=item.notes,
            )
            self.db.add(it_item)

        await self.db.flush()
        return version_id

    async def get_version_by_id(self, version_id: UUID) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(ItineraryVersion).where(ItineraryVersion.id == version_id)
        )
        version = result.scalar_one_or_none()
        if not version:
            return None
        return {
            "id": version.id,
            "trip_id": str(version.trip_id),
            "version_no": version.version_no,
            "reason": version.reason,
            "created_by": version.created_by,
            "proposal_id": str(version.proposal_id) if version.proposal_id else None,
            "run_id": str(version.run_id) if version.run_id else None,
            "total_cost": version.total_cost,
            "summary": version.summary,
            "created_at": version.created_at.isoformat() if version.created_at else None,
        }


class SQLAlchemyProposalRepository(ProposalRepository):
    """SQLAlchemy adapter for ProposalRepository protocol."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save_proposal(self, proposal: ReplanProposal) -> None:
        from app.db.models import ProposalStatus

        model = ProposalModel(
            id=proposal.id,
            trip_id=proposal.trip_id,
            run_id=proposal.run_id,
            base_version_id=proposal.base_version_id,
            status=ProposalStatus(proposal.status),
            reason=proposal.reason,
            explanation=proposal.explanation,
            disruption_ids=proposal.disruptions and [str(d.id) for d in proposal.disruptions] or [],
            diff=proposal.diff,
            proposed_items=[i.model_dump() for i in proposal.proposed_items] if proposal.proposed_items else [],
            cost_delta=proposal.cost_delta,
            time_delta_min=proposal.time_delta_min,
            items_changed=proposal.items_changed,
            alternatives_of=proposal.alternatives_of,
            resulting_version_id=proposal.resulting_version_id,
            decided_at=proposal.created_at,
            decision_note=None,
        )
        self.db.add(model)
        await self.db.flush()

    async def get_proposal(self, proposal_id: UUID) -> ReplanProposal | None:
        result = await self.db.execute(
            select(ProposalModel).where(ProposalModel.id == proposal_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None

        disruptions = []
        for d in model.disruption_ids:
            disruptions.append(DisruptionEvent(id=UUID(d)))

        return ReplanProposal(
            id=model.id,
            trip_id=model.trip_id,
            run_id=model.run_id,
            base_version_id=model.base_version_id,
            status=model.status.value if model.status else "pending",
            reason=model.reason,
            explanation=model.explanation,
            disruptions=disruptions,
            diff=model.diff or [],
            proposed_items=[DraftItem(**i) for i in (model.proposed_items or [])],
            cost_delta=model.cost_delta or Decimal(0),
            time_delta_min=model.time_delta_min or 0,
            items_changed=model.items_changed or 0,
            alternatives_of=model.alternatives_of,
            resulting_version_id=model.resulting_version_id,
        )

    async def update_proposal_status(
        self,
        proposal_id: UUID,
        status: str,
        resulting_version_id: UUID | None = None,
        note: str | None = None,
    ) -> None:
        result = await self.db.execute(
            select(ProposalModel).where(ProposalModel.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        if proposal:
            proposal.status = status
            if resulting_version_id:
                proposal.resulting_version_id = resulting_version_id
            if note:
                proposal.decision_note = note
            await self.db.flush()

    async def get_pending_proposals(self, trip_id: UUID) -> list[ReplanProposal]:
        result = await self.db.execute(
            select(ProposalModel)
            .where(
                ProposalModel.trip_id == trip_id,
                ProposalModel.status == "pending",
            )
            .order_by(ProposalModel.created_at.desc())
        )
        models = result.scalars().all()

        proposals = []
        for m in models:
            disruptions = []
            for d in m.disruption_ids:
                disruptions.append(DisruptionEvent(id=UUID(d)))

            proposals.append(ReplanProposal(
                id=m.id,
                trip_id=m.trip_id,
                run_id=m.run_id,
                base_version_id=m.base_version_id,
                status=m.status.value if m.status else "pending",
                reason=m.reason,
                explanation=m.explanation,
                disruptions=disruptions,
                diff=m.diff or [],
                proposed_items=[DraftItem(**i) for i in (m.proposed_items or [])],
                cost_delta=m.cost_delta or Decimal(0),
                time_delta_min=m.time_delta_min or 0,
                items_changed=m.items_changed or 0,
                alternatives_of=m.alternatives_of,
                resulting_version_id=m.resulting_version_id,
            ))
        return proposals


class SQLAlchemyDisruptionRepository(DisruptionRepository):
    """SQLAlchemy adapter for DisruptionRepository protocol."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save_disruption(self, disruption: DisruptionEvent) -> None:
        from app.db.models import DisruptionEvent as DisruptionModel, DisruptionType, SeverityType

        model = DisruptionModel(
            id=disruption.id,
            trip_id=disruption.trip_id,
            run_id=disruption.run_id,
            type=DisruptionType(disruption.type),
            severity=SeverityType(disruption.severity),
            day_index=disruption.day_index,
            window_start=disruption.window_start,
            window_end=disruption.window_end,
            affected_stable_keys=disruption.affected_stable_keys,
            summary=disruption.summary,
            source=disruption.source,
            data=disruption.data,
            fingerprint=disruption.fingerprint,
            is_simulated=True,
        )
        self.db.add(model)
        await self.db.flush()

    async def get_disruption_by_fingerprint(
        self, trip_id: UUID, fingerprint: str
    ) -> DisruptionEvent | None:
        result = await self.db.execute(
            select(DisruptionModel)
            .where(
                DisruptionModel.trip_id == trip_id,
                DisruptionModel.fingerprint == fingerprint,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return DisruptionEvent(
            id=model.id,
            trip_id=model.trip_id,
            type=model.type.value if model.type else None,
            severity=model.severity.value if model.severity else "medium",
            day_index=model.day_index,
            window_start=model.window_start,
            window_end=model.window_end,
            affected_stable_keys=model.affected_stable_keys,
            summary=model.summary,
            source=model.source,
            data=model.data,
            fingerprint=model.fingerprint,
        )

    async def get_active_disruptions(self, trip_id: UUID) -> list[DisruptionEvent]:
        result = await self.db.execute(
            select(DisruptionModel).where(DisruptionModel.trip_id == trip_id)
        )
        models = result.scalars().all()

        disruptions = []
        for m in models:
            disruptions.append(DisruptionEvent(
                id=m.id,
                trip_id=m.trip_id,
                type=m.type.value if m.type else None,
                severity=m.severity.value if m.severity else "medium",
                day_index=m.day_index,
                window_start=m.window_start,
                window_end=m.window_end,
                affected_stable_keys=m.affected_stable_keys,
                summary=m.summary,
                source=m.source,
                data=m.data,
                fingerprint=m.fingerprint,
            ))
        return disruptions

    async def resolve_disruption(self, disruption_id: UUID) -> None:
        await self.db.execute(
            DisruptionModel.__table__.delete().where(
                DisruptionModel.id == disruption_id
            )
        )
        await self.db.flush()


class SQLAlchemyPlaceCatalogRepository(PlaceCatalogRepository):
    """SQLAlchemy adapter for PlaceCatalogRepository protocol.

    This is a read-only adapter for the seed catalog. Actual place data
    comes from external APIs; this just manages the seed cache.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search_places(
        self,
        city: str,
        query: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 30,
    ) -> list[PlaceCandidate]:
        from app.db.models import Place
        stmt = select(Place)
        if city:
            stmt = stmt.where(Place.city.ilike(f"%{city}%"))
        if query:
            stmt = stmt.where(or_(Place.name.ilike(f"%{query}%"), Place.description.ilike(f"%{query}%")))
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        places = result.scalars().all()

        return [
            PlaceCandidate(
                id=p.id,
                external_id=p.external_id,
                name=p.name,
                city=p.city,
                country=p.country,
                category=p.category.value if p.category else "other",
                setting=p.setting.value if p.setting else "mixed",
                avg_cost=p.avg_cost or Decimal(0),
                currency=p.currency,
                avg_duration_min=p.avg_duration_min,
                opening_hours=p.opening_hours,
                hours_confidence=p.hours_confidence,
                lat=p.lat,
                lng=p.lng,
                rating=p.rating,
                tags=p.tags,
                description=p.description,
                raw=p.raw,
            )
            for p in places
        ]

    async def get_place_by_id(self, place_id: UUID) -> PlaceCandidate | None:
        from app.db.models import Place

        result = await self.db.execute(
            select(Place).where(Place.id == place_id)
        )
        place = result.scalar_one_or_none()
        if not place:
            return None

        return PlaceCandidate(
            id=place.id,
            external_id=place.external_id,
            name=place.name,
            city=place.city,
            country=place.country,
            category=place.category.value if place.category else "other",
            setting=place.setting.value if place.setting else "mixed",
            avg_cost=place.avg_cost or Decimal(0),
            currency=place.currency,
            avg_duration_min=place.avg_duration_min,
            opening_hours=place.opening_hours,
            hours_confidence=place.hours_confidence,
            lat=place.lat,
            lng=place.lng,
            rating=place.rating,
            tags=place.tags,
            description=place.description,
            raw=place.raw,
        )

    async def upsert_place(self, place: PlaceCandidate) -> None:
        from app.db.models import Place

        result = await self.db.execute(
            select(Place).where(
                (Place.id == place.id)
                | ((Place.source == "seed") & (Place.external_id == place.external_id))
            )
        )
        db_place = result.scalars().first()

        if not db_place:
            db_place = Place(id=place.id)
            self.db.add(db_place)

        db_place.external_id = place.external_id
        db_place.source = "seed"
        db_place.name = place.name
        db_place.city = place.city
        db_place.country = place.country
        db_place.category = place.category
        db_place.setting = place.setting
        db_place.avg_cost = place.avg_cost
        db_place.currency = place.currency
        db_place.avg_duration_min = place.avg_duration_min
        db_place.opening_hours = place.opening_hours
        db_place.hours_confidence = place.hours_confidence
        db_place.lat = place.lat
        db_place.lng = place.lng
        db_place.rating = place.rating
        db_place.tags = place.tags
        db_place.description = place.description
        db_place.raw = place.raw
        await self.db.flush()


class SQLAlchemyExpenseRepository(ExpenseRepository):
    """SQLAlchemy adapter for ExpenseRepository protocol."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_expenses(self, trip_id: UUID) -> list[dict[str, Any]]:
        from app.db.models import Expense

        result = await self.db.execute(
            select(Expense).where(Expense.trip_id == trip_id)
        )
        expenses = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "trip_id": str(e.trip_id),
                "category": e.category.value if e.category else "other",
                "amount": float(e.amount) if e.amount else 0,
                "currency": e.currency,
                "description": e.description,
                "item_stable_key": str(e.item_stable_key) if e.item_stable_key else None,
                "spent_at": e.spent_at.isoformat() if e.spent_at else None,
            }
            for e in expenses
        ]

    async def get_expenses_summary(self, trip_id: UUID) -> dict[str, Any]:
        from app.db.models import Expense

        result = await self.db.execute(
            select(Expense.category, func.sum(Expense.amount))
            .where(Expense.trip_id == trip_id)
            .group_by(Expense.category)
        )
        rows = result.all()

        total = sum(float(r[1] or 0) for r in rows)
        by_category = {r[0].value if r[0] else "other": float(r[1] or 0) for r in rows}
        count = await self.db.execute(
            select(func.count(Expense.id)).where(Expense.trip_id == trip_id)
        )
        expense_count = count.scalar_one_or_none() or 0

        return {
            "total": total,
            "by_category": by_category,
            "count": expense_count,
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
        from app.db.models import Expense, ExpenseCategory

        expense_id = uuid4()
        expense = Expense(
            id=expense_id,
            trip_id=trip_id,
            category=ExpenseCategory(category),
            amount=amount,
            currency=currency,
            description=description,
            item_stable_key=item_stable_key,
        )
        self.db.add(expense)
        await self.db.flush()
        return expense_id


class SQLAlchemyCacheRepository(CacheRepository):
    """SQLAlchemy adapter for CacheRepository protocol.

    Stores cached data in-memory for the duration of a run since
    the cache is primarily used for rate-limited external API calls.
    For production use, this could be backed by Redis.
    """

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> dict[str, Any] | None:
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            if entry.get("expires_at", datetime.min.replace(tzinfo=UTC)) < datetime.now(UTC):
                del self._cache[key]
                return None
            return entry.get("data")

    async def set(
        self, key: str, provider: str, data: dict[str, Any], ttl_seconds: int = 3600
    ) -> None:
        async with self._lock:
            expires_at = datetime.now(UTC).timestamp() + ttl_seconds
            self._cache[key] = {
                "provider": provider,
                "data": data,
                "expires_at": expires_at,
            }


class SQLAlchemyRunEventRepository(RunEventRepository):
    """SQLAlchemy adapter for RunEventRepository protocol."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_event(self, run_id: UUID, event: AgentEvent) -> int:
        # NOTE: We do NOT persist here. The backend's AgentGateway._publish()
        # handles all persistence + broadcasting. This method only computes
        # the next sequence number so the gateway's internal bookkeeping
        # stays consistent with what _publish() will eventually write.
        result = await self.db.execute(
            select(func.max(AgentRunEvent.seq))
            .where(AgentRunEvent.run_id == run_id)
        )
        max_seq = result.scalar_one_or_none()
        return (max_seq or 0) + 1

    async def get_events(self, run_id: UUID, after_seq: int = 0) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(AgentRunEvent)
            .where(
                AgentRunEvent.run_id == run_id,
                AgentRunEvent.seq > after_seq,
            )
            .order_by(AgentRunEvent.seq)
        )
        events = result.scalars().all()

        return [
            {
                "seq": e.seq,
                "type": e.type,
                "node": e.node,
                "message": e.message,
                "status": e.status,
                "payload": e.payload or {},
                "latency_ms": e.latency_ms,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]


class RepositoriesBundle:
    """SQLAlchemy-backed bundle of repository adapters."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._trips: SQLAlchemyTripRepository | None = None
        self._itineraries: SQLAlchemyItineraryRepository | None = None
        self._proposals: SQLAlchemyProposalRepository | None = None
        self._disruptions: SQLAlchemyDisruptionRepository | None = None
        self._places: SQLAlchemyPlaceCatalogRepository | None = None
        self._expenses: SQLAlchemyExpenseRepository | None = None
        self._cache: SQLAlchemyCacheRepository | None = None
        self._run_events: SQLAlchemyRunEventRepository | None = None

    @property
    def trips(self) -> SQLAlchemyTripRepository:
        if self._trips is None:
            self._trips = SQLAlchemyTripRepository(self._db)
        return self._trips

    @property
    def itineraries(self) -> SQLAlchemyItineraryRepository:
        if self._itineraries is None:
            self._itineraries = SQLAlchemyItineraryRepository(self._db)
        return self._itineraries

    @property
    def proposals(self) -> SQLAlchemyProposalRepository:
        if self._proposals is None:
            self._proposals = SQLAlchemyProposalRepository(self._db)
        return self._proposals

    @property
    def disruptions(self) -> SQLAlchemyDisruptionRepository:
        if self._disruptions is None:
            self._disruptions = SQLAlchemyDisruptionRepository(self._db)
        return self._disruptions

    @property
    def places(self) -> SQLAlchemyPlaceCatalogRepository:
        if self._places is None:
            self._places = SQLAlchemyPlaceCatalogRepository(self._db)
        return self._places

    @property
    def expenses(self) -> SQLAlchemyExpenseRepository:
        if self._expenses is None:
            self._expenses = SQLAlchemyExpenseRepository(self._db)
        return self._expenses

    @property
    def cache(self) -> SQLAlchemyCacheRepository:
        if self._cache is None:
            self._cache = SQLAlchemyCacheRepository()
        return self._cache

    @property
    def run_events(self) -> SQLAlchemyRunEventRepository:
        if self._run_events is None:
            self._run_events = SQLAlchemyRunEventRepository(self._db)
        return self._run_events