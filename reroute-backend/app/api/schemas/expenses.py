"""Expenses API schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Request schemas
class ExpenseCreate(BaseModel):
    category: str
    amount: Decimal = Field(..., gt=0)
    currency: Optional[str] = None
    description: Optional[str] = None
    spent_at: Optional[datetime] = None
    item_stable_key: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


# Response schemas
class ExpenseOut(BaseModel):
    id: UUID
    trip_id: UUID
    user_id: UUID
    item_stable_key: Optional[UUID] = None
    category: str
    amount: float
    currency: str
    amount_in_trip_currency: float
    description: Optional[str] = None
    spent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BudgetOut(BaseModel):
    planned_total: float
    actual_total: float
    remaining: float
    overrun_pct: float
    by_category: List[dict]

    model_config = ConfigDict(from_attributes=True)