"""Expenses service: handles trip expenses and budget."""
from __future__ import annotations

from typing import Optional, List
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models import Expense, Trip, User, ExpenseCategory


class ExpensesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_expense(
        self, trip_id: UUID, user_id: UUID, category: str, amount: float,
        currency: str = "INR", description: Optional[str] = None,
        spent_at: Optional[datetime] = None, item_stable_key: Optional[UUID] = None
    ) -> Expense:
        """Create a new expense for a trip."""
        trip = await self.db.get(Trip, trip_id)
        user = await self.db.get(User, user_id)

        if not trip or trip.user_id != user_id:
            raise ValueError("Trip not found or access denied")

        # Convert amount to trip currency if different
        amount_in_trip_currency = amount
        if currency != trip.currency:
            # TODO: implement currency conversion
            amount_in_trip_currency = amount  # placeholder

        expense = Expense(
            id=uuid4(),
            trip_id=trip_id,
            user_id=user_id,
            item_stable_key=item_stable_key,
            category=ExpenseCategory(category),
            amount=Decimal(str(amount)),
            currency=currency,
            amount_in_trip_currency=Decimal(str(amount_in_trip_currency)),
            description=description,
            spent_at=spent_at or datetime.utcnow(),
        )
        self.db.add(expense)
        await self.db.flush()
        return expense

    async def get_expenses(self, trip_id: UUID, user_id: UUID) -> List[Expense]:
        """Get all expenses for a trip."""
        trip = await self.db.get(Trip, trip_id)
        if not trip or trip.user_id != user_id:
            raise ValueError("Trip not found or access denied")

        result = await self.db.execute(
            select(Expense).where(Expense.trip_id == trip_id)
        )
        return result.scalars().all()

    async def delete_expense(self, expense_id: UUID, user_id: UUID) -> bool:
        """Delete an expense (user must own it)."""
        expense = await self.db.get(Expense, expense_id)
        if not expense or expense.user_id != user_id:
            return False

        await self.db.delete(expense)
        await self.db.flush()
        return True

    async def get_budget(self, trip_id: UUID, user_id: UUID) -> dict:
        """Get budget summary for a trip."""
        trip = await self.db.get(Trip, trip_id)
        if not trip or trip.user_id != user_id:
            raise ValueError("Trip not found or access denied")

        # Get total planned budget
        planned_total = float(trip.budget_total or 0)

        # Get actual expenses
        result = await self.db.execute(
            select(func.sum(Expense.amount_in_trip_currency)).where(Expense.trip_id == trip_id)
        )
        actual_total = float(result.scalar() or 0)

        remaining = planned_total - actual_total
        overrun_pct = ((actual_total - planned_total) / planned_total * 100) if planned_total > 0 else 0

        # Get expenses by category
        result = await self.db.execute(
            select(Expense.category, func.sum(Expense.amount_in_trip_currency))
            .where(Expense.trip_id == trip_id)
            .group_by(Expense.category)
        )
        expenses_by_category = []
        for category, total in result.fetchall():
            expenses_by_category.append({
                "category": category.value,
                "planned": 0,  # TODO: calculate planned budget per category if implemented
                "actual": float(total or 0)
            })

        return {
            "planned_total": planned_total,
            "actual_total": actual_total,
            "remaining": remaining,
            "overrun_pct": overrun_pct,
            "by_category": expenses_by_category
        }