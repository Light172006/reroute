from typing import List, Optional, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import Trip, PaceType, TripStatus


class TripService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_trip(
        self,
        user_id: Any,
        title: str,
        destination: str,
        start_date: Any,
        end_date: Any,
        group_size: int = 1,
        budget_total: float = 0.0,
        budget_per_day_cap: Optional[float] = None,
        currency: str = "INR",
        pace: str = "balanced",
        vibe_tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> Trip:
        pace_enum = PaceType.balanced
        if pace in PaceType.__members__:
            pace_enum = PaceType[pace]

        trip = Trip(
            user_id=user_id,
            title=title,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            group_size=group_size,
            budget_total=budget_total,
            budget_per_day_cap=budget_per_day_cap,
            currency=currency,
            pace=pace_enum,
            vibe_tags=vibe_tags or [],
            notes=notes,
            status=TripStatus.draft,
        )
        self.db.add(trip)
        await self.db.flush()
        return trip

    async def get_trip(self, trip_id: Any) -> Optional[Trip]:
        result = await self.db.execute(select(Trip).where(Trip.id == trip_id))
        return result.scalar_one_or_none()

    async def list_trips(self, user_id: Any) -> List[Trip]:
        result = await self.db.execute(
            select(Trip).where(Trip.user_id == user_id).order_by(Trip.created_at.desc())
        )
        return result.scalars().all()

    async def update_trip(self, trip_id: Any, user_id: Any, **fields) -> Optional[Trip]:
        trip = await self.get_trip(trip_id)
        if not trip or str(trip.user_id) != str(user_id):
            return None

        for k, v in fields.items():
            if v is not None and hasattr(trip, k):
                if k == "pace" and isinstance(v, str):
                    if v in PaceType.__members__:
                        setattr(trip, k, PaceType[v])
                elif k == "status" and isinstance(v, str):
                    if v in TripStatus.__members__:
                        setattr(trip, k, TripStatus[v])
                else:
                    setattr(trip, k, v)

        trip.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return trip

    async def delete_trip(self, trip_id: Any, user_id: Any) -> bool:
        trip = await self.get_trip(trip_id)
        if not trip or str(trip.user_id) != str(user_id):
            return False

        await self.db.delete(trip)
        await self.db.flush()
        return True
