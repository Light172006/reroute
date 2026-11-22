"""Itinerary service: handles itinerary versions, items, and diff logic."""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.db.models import (
    Trip, ItineraryVersion, ItineraryItem, Place, User,
    ItemType, SettingType, TransportMode
)


class ItineraryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_current_itinerary(self, trip_id: UUID, user_id: UUID) -> Optional[dict]:
        """Get the current itinerary version with items grouped by day."""
        trip = await self.db.get(Trip, trip_id)
        if not trip or trip.user_id != user_id:
            return None

        current_version_id = trip.current_version_id
        if not current_version_id:
            return {
                "trip_id": str(trip_id),
                "version": None,
                "days": []
            }

        version = await self.db.get(ItineraryVersion, current_version_id)
        if not version:
            return {
                "trip_id": str(trip_id),
                "version": None,
                "days": []
            }

        # Load items with places
        result = await self.db.execute(
            select(ItineraryItem)
            .options(selectinload(ItineraryItem.place))
            .where(ItineraryItem.version_id == current_version_id)
            .order_by(ItineraryItem.day_index, ItineraryItem.position)
        )
        items = result.scalars().all()

        return self._build_itinerary_response(trip_id, version, items, trip=trip)

    async def list_versions(self, trip_id: UUID, user_id: UUID) -> List[dict]:
        """List all itinerary versions for a trip."""
        trip = await self.db.get(Trip, trip_id)
        if not trip or trip.user_id != user_id:
            return []

        result = await self.db.execute(
            select(ItineraryVersion)
            .where(ItineraryVersion.trip_id == trip_id)
            .order_by(ItineraryVersion.version_no.desc())
        )
        versions = result.scalars().all()

        return [
            {
                "id": str(v.id),
                "version_no": v.version_no,
                "reason": v.reason,
                "created_by": v.created_by,
                "total_cost": float(v.total_cost) if v.total_cost else 0,
                "summary": v.summary,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

    async def get_version(self, trip_id: UUID, version_id: UUID, user_id: UUID) -> Optional[dict]:
        """Get a specific itinerary version."""
        trip = await self.db.get(Trip, trip_id)
        if not trip or trip.user_id != user_id:
            return None

        version = await self.db.get(ItineraryVersion, version_id)
        if not version or version.trip_id != trip_id:
            return None

        result = await self.db.execute(
            select(ItineraryItem)
            .options(selectinload(ItineraryItem.place))
            .where(ItineraryItem.version_id == version_id)
            .order_by(ItineraryItem.day_index, ItineraryItem.position)
        )
        items = result.scalars().all()

        return self._build_itinerary_response(trip_id, version, items, trip=trip)

    async def diff_versions(
        self, trip_id: UUID, from_version_id: UUID, to_version_id: UUID, user_id: UUID
    ) -> Optional[List[dict]]:
        """Diff two versions matched by stable_key."""
        trip = await self.db.get(Trip, trip_id)
        if not trip or trip.user_id != user_id:
            return None

        # Get items for both versions
        from_items = await self._get_version_items(from_version_id)
        to_items = await self._get_version_items(to_version_id)

        if not from_items or not to_items:
            return None

        # Match by stable_key
        from_by_key = {item.stable_key: item for item in from_items if item.stable_key}
        to_by_key = {item.stable_key: item for item in to_items if item.stable_key}

        all_keys = set(from_by_key.keys()) | set(to_by_key.keys())
        diff = []

        for key in all_keys:
            from_item = from_by_key.get(key)
            to_item = to_by_key.get(key)

            if from_item and not to_item:
                # Deleted
                diff.append({
                    "op": "delete",
                    "day": from_item.day_index,
                    "stable_key": str(key),
                    "before": self._item_to_dict(from_item),
                    "after": None,
                    "why": "Item removed"
                })
            elif not from_item and to_item:
                # Added
                diff.append({
                    "op": "add",
                    "day": to_item.day_index,
                    "stable_key": str(key),
                    "before": None,
                    "after": self._item_to_dict(to_item),
                    "why": "New item added"
                })
            elif from_item and to_item:
                # Check for changes
                changes = self._compare_items(from_item, to_item)
                if changes:
                    diff.append({
                        "op": "replace",
                        "day": to_item.day_index,
                        "stable_key": str(key),
                        "before": self._item_to_dict(from_item),
                        "after": self._item_to_dict(to_item),
                        "why": "; ".join(changes)
                    })

        return diff

    async def restore_version(
        self, trip_id: UUID, version_id: UUID, user_id: UUID, reason: str = "Restored from previous version"
    ) -> Optional[dict]:
        """Create a new version copying an old one."""
        trip = await self.db.get(Trip, trip_id)
        if not trip or trip.user_id != user_id:
            return None

        source_version = await self.db.get(ItineraryVersion, version_id)
        if not source_version or source_version.trip_id != trip_id:
            return None

        # Get items from source version
        result = await self.db.execute(
            select(ItineraryItem)
            .options(selectinload(ItineraryItem.place))
            .where(ItineraryItem.version_id == version_id)
            .order_by(ItineraryItem.day_index, ItineraryItem.position)
        )
        source_items = result.scalars().all()

        # Create new version
        new_version_no = await self._get_next_version_no(trip_id)
        new_version = ItineraryVersion(
            id=uuid.uuid4(),
            trip_id=trip_id,
            version_no=new_version_no,
            reason=reason,
            created_by="user:restore",
            total_cost=source_version.total_cost,
            summary=source_version.summary,
        )
        self.db.add(new_version)
        await self.db.flush()

        # Copy items with new stable_keys
        for item in source_items:
            new_item = ItineraryItem(
                id=uuid.uuid4(),
                version_id=new_version.id,
                stable_key=uuid.uuid4(),  # new stable_key for the copy
                day_index=item.day_index,
                position=item.position,
                place_id=item.place_id,
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
                flags=item.flags,
                notes=item.notes,
            )
            self.db.add(new_item)

        # Update trip's current version
        trip.current_version_id = new_version.id
        trip.status = "planned"
        trip.updated_at = datetime.now()

        await self.db.commit()

        return await self.get_current_itinerary(trip_id, user_id)

    async def update_item(
        self, trip_id: UUID, item_id: UUID, user_id: UUID,
        is_locked: Optional[bool] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[dict]:
        """Update an item (creates new version)."""
        trip = await self.db.get(Trip, trip_id)
        if not trip or trip.user_id != user_id:
            return None

        current_version_id = trip.current_version_id
        if not current_version_id:
            return None

        # Get the item
        item = await self.db.get(ItineraryItem, item_id)
        if not item or item.version_id != current_version_id:
            return None

        # Create new version
        new_version_no = await self._get_next_version_no(trip_id)
        new_version = ItineraryVersion(
            id=uuid.uuid4(),
            trip_id=trip_id,
            version_no=new_version_no,
            reason=f"Manual edit: {item.title}",
            created_by="user:edit",
            total_cost=0,  # will recalc
            summary="",
        )
        self.db.add(new_version)
        await self.db.flush()

        # Copy all items from current version, modifying the target item
        result = await self.db.execute(
            select(ItineraryItem)
            .options(selectinload(ItineraryItem.place))
            .where(ItineraryItem.version_id == current_version_id)
            .order_by(ItineraryItem.day_index, ItineraryItem.position)
        )
        current_items = result.scalars().all()

        total_cost = 0
        for current_item in current_items:
            if current_item.id == item_id:
                # Modified item
                new_item = ItineraryItem(
                    id=uuid.uuid4(),
                    version_id=new_version.id,
                    stable_key=current_item.stable_key,  # keep stable_key for diffing
                    day_index=current_item.day_index,
                    position=current_item.position,
                    place_id=current_item.place_id,
                    title=current_item.title,
                    category=current_item.category,
                    setting=current_item.setting,
                    start_time=start_time if start_time is not None else current_item.start_time,
                    end_time=end_time if end_time is not None else current_item.end_time,
                    est_cost=current_item.est_cost,
                    lat=current_item.lat,
                    lng=current_item.lng,
                    is_locked=is_locked if is_locked is not None else current_item.is_locked,
                    travel_mode=current_item.travel_mode,
                    travel_minutes=current_item.travel_minutes,
                    flags=current_item.flags,
                    notes=notes if notes is not None else current_item.notes,
                )
            else:
                # Unchanged item - copy with same stable_key
                new_item = ItineraryItem(
                    id=uuid.uuid4(),
                    version_id=new_version.id,
                    stable_key=current_item.stable_key,
                    day_index=current_item.day_index,
                    position=current_item.position,
                    place_id=current_item.place_id,
                    title=current_item.title,
                    category=current_item.category,
                    setting=current_item.setting,
                    start_time=current_item.start_time,
                    end_time=current_item.end_time,
                    est_cost=current_item.est_cost,
                    lat=current_item.lat,
                    lng=current_item.lng,
                    is_locked=current_item.is_locked,
                    travel_mode=current_item.travel_mode,
                    travel_minutes=current_item.travel_minutes,
                    flags=current_item.flags,
                    notes=current_item.notes,
                )
            self.db.add(new_item)
            total_cost += float(new_item.est_cost) if new_item.est_cost else 0

        new_version.total_cost = total_cost
        new_version.summary = f"{len(current_items)} items, updated {item.title}"

        # Update trip
        trip.current_version_id = new_version.id
        trip.updated_at = datetime.now()

        await self.db.commit()

        return await self.get_current_itinerary(trip_id, user_id)

    async def delete_item(self, trip_id: UUID, item_id: UUID, user_id: UUID) -> Optional[dict]:
        """Delete an item (creates new version)."""
        trip = await self.db.get(Trip, trip_id)
        if not trip or trip.user_id != user_id:
            return None

        current_version_id = trip.current_version_id
        if not current_version_id:
            return None

        item = await self.db.get(ItineraryItem, item_id)
        if not item or item.version_id != current_version_id:
            return None

        # Create new version
        new_version_no = await self._get_next_version_no(trip_id)
        new_version = ItineraryVersion(
            id=uuid.uuid4(),
            trip_id=trip_id,
            version_no=new_version_no,
            reason=f"Deleted: {item.title}",
            created_by="user:delete",
            total_cost=0,
            summary="",
        )
        self.db.add(new_version)
        await self.db.flush()

        # Copy all items except the deleted one
        result = await self.db.execute(
            select(ItineraryItem)
            .options(selectinload(ItineraryItem.place))
            .where(ItineraryItem.version_id == current_version_id)
            .order_by(ItineraryItem.day_index, ItineraryItem.position)
        )
        current_items = result.scalars().all()

        total_cost = 0
        for current_item in current_items:
            if current_item.id == item_id:
                continue  # skip deleted item
            new_item = ItineraryItem(
                id=uuid.uuid4(),
                version_id=new_version.id,
                stable_key=current_item.stable_key,
                day_index=current_item.day_index,
                position=current_item.position,
                place_id=current_item.place_id,
                title=current_item.title,
                category=current_item.category,
                setting=current_item.setting,
                start_time=current_item.start_time,
                end_time=current_item.end_time,
                est_cost=current_item.est_cost,
                lat=current_item.lat,
                lng=current_item.lng,
                is_locked=current_item.is_locked,
                travel_mode=current_item.travel_mode,
                travel_minutes=current_item.travel_minutes,
                flags=current_item.flags,
                notes=current_item.notes,
            )
            self.db.add(new_item)
            total_cost += float(new_item.est_cost) if new_item.est_cost else 0

        new_version.total_cost = total_cost
        new_version.summary = f"{len(current_items) - 1} items, deleted {item.title}"

        # Reorder positions in affected day
        await self._reorder_positions(new_version.id)

        # Update trip
        trip.current_version_id = new_version.id
        trip.updated_at = datetime.now()

        await self.db.commit()

        return await self.get_current_itinerary(trip_id, user_id)

    async def reorder_items(
        self, trip_id: UUID, user_id: UUID, day_index: int, ordered_stable_keys: List[UUID]
    ) -> Optional[dict]:
        """Reorder items within a day (creates new version)."""
        trip = await self.db.get(Trip, trip_id)
        if not trip or trip.user_id != user_id:
            return None

        current_version_id = trip.current_version_id
        if not current_version_id:
            return None

        # Create new version
        new_version_no = await self._get_next_version_no(trip_id)
        new_version = ItineraryVersion(
            id=uuid.uuid4(),
            trip_id=trip_id,
            version_no=new_version_no,
            reason=f"Reordered Day {day_index}",
            created_by="user:reorder",
            total_cost=0,
            summary="",
        )
        self.db.add(new_version)
        await self.db.flush()

        # Get all items from current version
        result = await self.db.execute(
            select(ItineraryItem)
            .options(selectinload(ItineraryItem.place))
            .where(ItineraryItem.version_id == current_version_id)
            .order_by(ItineraryItem.day_index, ItineraryItem.position)
        )
        current_items = result.scalars().all()

        # Build mapping of stable_key to item
        items_by_key = {item.stable_key: item for item in current_items if item.stable_key}

        # Reorder items in the specified day
        new_items_in_day = []
        for pos, stable_key in enumerate(ordered_stable_keys):
            if stable_key in items_by_key:
                item = items_by_key[stable_key]
                if item.day_index == day_index:
                    new_items_in_day.append((pos, item))

        total_cost = 0
        for current_item in current_items:
            # Determine new position
            new_position = current_item.position
            if current_item.day_index == day_index and current_item.stable_key in items_by_key:
                # Find new position from ordered list
                for pos, (new_pos, item) in enumerate(new_items_in_day):
                    if item.stable_key == current_item.stable_key:
                        new_position = new_pos
                        break

            new_item = ItineraryItem(
                id=uuid.uuid4(),
                version_id=new_version.id,
                stable_key=current_item.stable_key,
                day_index=current_item.day_index,
                position=new_position,
                place_id=current_item.place_id,
                title=current_item.title,
                category=current_item.category,
                setting=current_item.setting,
                start_time=current_item.start_time,
                end_time=current_item.end_time,
                est_cost=current_item.est_cost,
                lat=current_item.lat,
                lng=current_item.lng,
                is_locked=current_item.is_locked,
                travel_mode=current_item.travel_mode,
                travel_minutes=current_item.travel_minutes,
                flags=current_item.flags,
                notes=current_item.notes,
            )
            self.db.add(new_item)
            total_cost += float(new_item.est_cost) if new_item.est_cost else 0

        new_version.total_cost = total_cost
        new_version.summary = f"Reordered Day {day_index}"

        # Update trip
        trip.current_version_id = new_version.id
        trip.updated_at = datetime.now()

        await self.db.commit()

        return await self.get_current_itinerary(trip_id, user_id)

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    async def _get_version_items(self, version_id: UUID) -> List[ItineraryItem]:
        result = await self.db.execute(
            select(ItineraryItem)
            .options(selectinload(ItineraryItem.place))
            .where(ItineraryItem.version_id == version_id)
            .order_by(ItineraryItem.day_index, ItineraryItem.position)
        )
        return result.scalars().all()

    async def _get_next_version_no(self, trip_id: UUID) -> int:
        result = await self.db.execute(
            select(func.max(ItineraryVersion.version_no))
            .where(ItineraryVersion.trip_id == trip_id)
        )
        max_no = result.scalar_one_or_none()
        return (max_no or 0) + 1

    def _item_to_dict(self, item: ItineraryItem) -> dict:
        return {
            "id": str(item.id),
            "stable_key": str(item.stable_key) if item.stable_key else None,
            "position": item.position,
            "title": item.title,
            "category": item.category.value if item.category else None,
            "setting": item.setting.value if item.setting else None,
            "start_time": item.start_time.strftime("%H:%M") if item.start_time else None,
            "end_time": item.end_time.strftime("%H:%M") if item.end_time else None,
            "est_cost": float(item.est_cost) if item.est_cost else 0,
            "lat": item.lat,
            "lng": item.lng,
            "is_locked": item.is_locked,
            "flags": item.flags or [],
            "travel": {
                "mode": item.travel_mode.value if item.travel_mode else None,
                "minutes": item.travel_minutes,
                "distance_m": None,  # not stored in model
            },
            "place_id": str(item.place_id) if item.place_id else None,
            "notes": item.notes,
        }

    def _compare_items(self, from_item: ItineraryItem, to_item: ItineraryItem) -> List[str]:
        changes = []
        if from_item.title != to_item.title:
            changes.append(f"title: '{from_item.title}' -> '{to_item.title}'")
        if from_item.start_time != to_item.start_time:
            changes.append(f"start_time: {from_item.start_time} -> {to_item.start_time}")
        if from_item.end_time != to_item.end_time:
            changes.append(f"end_time: {from_item.end_time} -> {to_item.end_time}")
        if from_item.position != to_item.position:
            changes.append(f"position: {from_item.position} -> {to_item.position}")
        if from_item.is_locked != to_item.is_locked:
            changes.append(f"is_locked: {from_item.is_locked} -> {to_item.is_locked}")
        if float(from_item.est_cost or 0) != float(to_item.est_cost or 0):
            changes.append(f"est_cost: {from_item.est_cost} -> {to_item.est_cost}")
        if from_item.day_index != to_item.day_index:
            changes.append(f"day_index: {from_item.day_index} -> {to_item.day_index}")
        return changes

    def _build_itinerary_response(
        self, trip_id: UUID, version: ItineraryVersion, items: List[ItineraryItem], trip: Optional[Trip] = None
    ) -> dict:
        """Build the itinerary response grouped by day."""
        start_date = trip.start_date if (trip and trip.start_date) else None

        # Group items by day
        by_day: Dict[int, List[dict]] = {}
        for item in items:
            day_idx = item.day_index
            if day_idx not in by_day:
                by_day[day_idx] = []
            by_day[day_idx].append(self._item_to_dict(item))

        # Build days array
        days = []
        for day_idx in sorted(by_day.keys()):
            day_items = by_day[day_idx]
            day_cost = sum(item.get("est_cost", 0) for item in day_items)
            walking_min = sum(
                item.get("travel", {}).get("minutes", 0) or 0
                for item in day_items
                if item.get("travel", {}).get("mode") == "walk"
            )
            # Calculate active minutes
            if day_items:
                first_start = min(item["start_time"] for item in day_items if item.get("start_time"))
                last_end = max(item["end_time"] for item in day_items if item.get("end_time"))
                from datetime import time as dttime
                def parse_t(t): return dttime(int(t[:2]), int(t[3:]))
                active_min = (parse_t(last_end).hour * 60 + parse_t(last_end).minute) - (parse_t(first_start).hour * 60 + parse_t(first_start).minute)
            else:
                active_min = 0

            day_date = (start_date + timedelta(days=day_idx - 1)).isoformat() if start_date else None

            days.append({
                "day_index": day_idx,
                "date": day_date,
                "summary": {
                    "cost": day_cost,
                    "walking_min": walking_min,
                    "active_min": active_min,
                },
                "items": day_items,
            })

        return {
            "trip_id": str(trip_id),
            "version": {
                "id": str(version.id),
                "version_no": version.version_no,
                "reason": version.reason,
                "created_by": version.created_by,
                "total_cost": float(version.total_cost) if version.total_cost else 0,
                "summary": version.summary,
                "created_at": version.created_at.isoformat() if version.created_at else None,
            },
            "days": days,
        }

    async def _reorder_positions(self, version_id: UUID):
        """Reorder positions within each day to be sequential."""
        result = await self.db.execute(
            select(ItineraryItem)
            .where(ItineraryItem.version_id == version_id)
            .order_by(ItineraryItem.day_index, ItineraryItem.position)
        )
        items = result.scalars().all()

        by_day: Dict[int, List[ItineraryItem]] = {}
        for item in items:
            by_day.setdefault(item.day_index, []).append(item)

        for day_items in by_day.values():
            day_items.sort(key=lambda x: x.position)
            for pos, item in enumerate(day_items):
                item.position = pos
                item.updated_at = datetime.now()