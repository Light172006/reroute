"""Places router: search the cached catalog for manual add."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.session import get_db
from app.db.models import Place, ItemType
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/places", tags=["places"])


@router.get("/search", status_code=status.HTTP_200_OK)
async def search_places(
    city: Optional[str] = Query(None, description="Filter by city"),
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search the cached catalog (for manual add)."""
    query = select(Place)

    if q:
        # Search in name and description
        search_pattern = f"%{q.lower()}%"
        query = query.where(
            or_(
                Place.name.ilike(search_pattern),
                Place.description.ilike(search_pattern),
            )
        )

    if city:
        query = query.where(Place.city.ilike(f"%{city}%"))

    if category:
        try:
            category_enum = ItemType(category)
            query = query.where(Place.category == category_enum)
        except ValueError:
            pass  # Invalid category, return empty

    query = query.limit(limit)
    result = await db.execute(query)
    places = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "city": p.city,
            "country": p.country,
            "category": p.category.value if p.category else None,
            "lat": p.lat,
            "lng": p.lng,
            "avg_cost": float(p.avg_cost) if p.avg_cost else 0,
            "avg_duration_min": p.avg_duration_min,
            "rating": p.rating,
            "description": p.description,
            "image_url": p.image_url,
            "tags": p.tags or [],
        }
        for p in places
    ]