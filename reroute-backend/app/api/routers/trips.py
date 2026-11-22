from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.services.trip_service import TripService
from app.services.itinerary_service import ItineraryService
from app.services.expenses_service import ExpensesService
from app.db.models import Trip
from app.api.schemas.trip import TripCreate, TripUpdate, TripOut
from app.api.schemas.itinerary import (
    ItemUpdate, ReorderRequest, RestoreVersionRequest,
    ItineraryResponse, DiffItem
)
from app.api.schemas.expenses import ExpenseCreate, ExpenseOut, BudgetOut
from app.api.dependencies import get_current_user

router = APIRouter()
items_router = APIRouter(prefix="/items", tags=["items"])


# ---------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------
async def get_trip_service(db: AsyncSession = Depends(get_db)) -> TripService:
    return TripService(db)

async def get_itinerary_service(db: AsyncSession = Depends(get_db)) -> ItineraryService:
    return ItineraryService(db)

async def get_expenses_service(db: AsyncSession = Depends(get_db)) -> ExpensesService:
    return ExpensesService(db)


# ---------------------------------------------------------------------
# Trip CRUD
# ---------------------------------------------------------------------
@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TripOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_trip(
    payload: TripCreate,
    user=Depends(get_current_user),
    svc: TripService = Depends(get_trip_service),
) -> Trip:
    trip = await svc.create_trip(
        user_id=user.id,
        title=payload.title,
        destination=payload.destination,
        start_date=payload.start_date,
        end_date=payload.end_date,
        group_size=payload.group_size,
        budget_total=payload.budget_total,
        budget_per_day_cap=payload.budget_per_day_cap,
        currency=payload.currency,
        pace=payload.pace,
        vibe_tags=payload.vibe_tags,
        notes=payload.notes,
    )
    return trip


@router.get("", response_model=List[TripOut])
@router.get("/", response_model=List[TripOut], include_in_schema=False)
async def list_trips(
    user=Depends(get_current_user), svc: TripService = Depends(get_trip_service)
) -> List[Trip]:
    return await svc.list_trips(user.id)


@router.get("/{trip_id}", response_model=TripOut)
async def get_trip(
    trip_id: str, user=Depends(get_current_user), svc: TripService = Depends(get_trip_service)
) -> Trip:
    trip = await svc.get_trip(trip_id)
    if not trip or str(trip.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.patch("/{trip_id}", response_model=TripOut)
async def update_trip(
    trip_id: str,
    payload: TripUpdate,
    user=Depends(get_current_user),
    svc: TripService = Depends(get_trip_service),
) -> Trip:
    trip = await svc.update_trip(trip_id, user.id, **payload.model_dump(exclude_unset=True))
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: str,
    user=Depends(get_current_user),
    svc: TripService = Depends(get_trip_service),
):
    success = await svc.delete_trip(trip_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Trip not found")
    return None


# ---------------------------------------------------------------------
# Itinerary endpoints
# ---------------------------------------------------------------------
@router.get("/{trip_id}/itinerary", response_model=ItineraryResponse)
async def get_itinerary(
    trip_id: UUID,
    user=Depends(get_current_user),
    svc: ItineraryService = Depends(get_itinerary_service),
):
    """Get current itinerary with items grouped by day."""
    result = await svc.get_current_itinerary(trip_id, user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return result


@router.get("/{trip_id}/versions", response_model=List[dict])
async def list_versions(
    trip_id: UUID,
    user=Depends(get_current_user),
    svc: ItineraryService = Depends(get_itinerary_service),
):
    """List all itinerary versions for a trip."""
    return await svc.list_versions(trip_id, user.id)


@router.get("/{trip_id}/versions/diff", response_model=List[DiffItem])
async def diff_versions(
    trip_id: UUID,
    from_version_id: UUID = Query(..., alias="from"),
    to_version_id: UUID = Query(..., alias="to"),
    user=Depends(get_current_user),
    svc: ItineraryService = Depends(get_itinerary_service),
):
    """Diff two versions matched by stable_key."""
    result = await svc.diff_versions(trip_id, from_version_id, to_version_id, user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trip or versions not found")
    return result


@router.get("/{trip_id}/versions/{version_id}", response_model=ItineraryResponse)
async def get_version(
    trip_id: UUID,
    version_id: UUID,
    user=Depends(get_current_user),
    svc: ItineraryService = Depends(get_itinerary_service),
):
    """Get a specific itinerary version."""
    result = await svc.get_version(trip_id, version_id, user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return result


@router.post("/{trip_id}/versions/{version_id}/restore", response_model=ItineraryResponse)
async def restore_version(
    trip_id: UUID,
    version_id: UUID,
    payload: RestoreVersionRequest,
    user=Depends(get_current_user),
    svc: ItineraryService = Depends(get_itinerary_service),
):
    """Restore a previous version (creates new version)."""
    result = await svc.restore_version(trip_id, version_id, user.id, payload.reason)
    if result is None:
        raise HTTPException(status_code=404, detail="Trip or version not found")
    return result


async def _handle_update_item(
    item_id: UUID,
    payload: ItemUpdate,
    user,
    svc: ItineraryService,
):
    from app.db.models import ItineraryItem, ItineraryVersion, Trip
    async with svc.db as db:
        item = await db.get(ItineraryItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        version = await db.get(ItineraryVersion, item.version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        trip = await db.get(Trip, version.trip_id)
        if not trip or trip.user_id != user.id:
            raise HTTPException(status_code=404, detail="Trip not found")

    result = await svc.update_item(
        trip_id=trip.id,
        item_id=item_id,
        user_id=user.id,
        is_locked=payload.is_locked,
        start_time=payload.start_time,
        end_time=payload.end_time,
        notes=payload.notes,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


async def _handle_delete_item(
    item_id: UUID,
    user,
    svc: ItineraryService,
):
    from app.db.models import ItineraryItem, ItineraryVersion, Trip
    async with svc.db as db:
        item = await db.get(ItineraryItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        version = await db.get(ItineraryVersion, item.version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        trip = await db.get(Trip, version.trip_id)
        if not trip or trip.user_id != user.id:
            raise HTTPException(status_code=404, detail="Trip not found")

    result = await svc.delete_item(trip_id=trip.id, item_id=item_id, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


# Item endpoints mounted on /items (frontend contract)
@items_router.patch("/{item_id}", response_model=ItineraryResponse)
async def update_item_standalone(
    item_id: UUID,
    payload: ItemUpdate,
    user=Depends(get_current_user),
    svc: ItineraryService = Depends(get_itinerary_service),
):
    return await _handle_update_item(item_id, payload, user, svc)


@items_router.delete("/{item_id}", response_model=ItineraryResponse)
async def delete_item_standalone(
    item_id: UUID,
    user=Depends(get_current_user),
    svc: ItineraryService = Depends(get_itinerary_service),
):
    return await _handle_delete_item(item_id, user, svc)


# Also mounted on trips router for /trips/items/{item_id}
@router.patch("/items/{item_id}", response_model=ItineraryResponse)
async def update_item(
    item_id: UUID,
    payload: ItemUpdate,
    user=Depends(get_current_user),
    svc: ItineraryService = Depends(get_itinerary_service),
):
    return await _handle_update_item(item_id, payload, user, svc)


@router.delete("/items/{item_id}", response_model=ItineraryResponse)
async def delete_item(
    item_id: UUID,
    user=Depends(get_current_user),
    svc: ItineraryService = Depends(get_itinerary_service),
):
    return await _handle_delete_item(item_id, user, svc)


@router.post("/{trip_id}/items/reorder", response_model=ItineraryResponse)
async def reorder_items(
    trip_id: UUID,
    payload: ReorderRequest,
    user=Depends(get_current_user),
    svc: ItineraryService = Depends(get_itinerary_service),
):
    """Reorder items within a day (creates new version)."""
    result = await svc.reorder_items(trip_id, user.id, payload.day_index, payload.ordered_stable_keys)
    if result is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return result


# ---------------------------------------------------------------------
# Expense endpoints
# ---------------------------------------------------------------------
@router.post("/{trip_id}/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    trip_id: UUID,
    payload: ExpenseCreate,
    user=Depends(get_current_user),
    svc: ExpensesService = Depends(get_expenses_service),
):
    """Create a new expense for a trip."""
    expense = await svc.create_expense(
        trip_id=trip_id,
        user_id=user.id,
        category=payload.category,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        spent_at=payload.spent_at,
        item_stable_key=payload.item_stable_key,
    )
    return expense


@router.get("/{trip_id}/expenses", response_model=List[ExpenseOut])
async def list_expenses(
    trip_id: UUID,
    user=Depends(get_current_user),
    svc: ExpensesService = Depends(get_expenses_service),
):
    """Get all expenses for a trip."""
    expenses = await svc.get_expenses(trip_id, user.id)
    return expenses


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: UUID,
    user=Depends(get_current_user),
    svc: ExpensesService = Depends(get_expenses_service),
):
    """Delete an expense by ID."""
    success = await svc.delete_expense(expense_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Expense not found")
    return None


@router.get("/{trip_id}/budget", response_model=BudgetOut)
async def get_budget(
    trip_id: UUID,
    user=Depends(get_current_user),
    svc: ExpensesService = Depends(get_expenses_service),
):
    """Get budget summary for a trip."""
    budget = await svc.get_budget(trip_id, user.id)
    return budget
