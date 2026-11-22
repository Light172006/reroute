"""Expense router: standalone expense endpoints for frontend API contract."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.expenses_service import ExpensesService
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/expenses", tags=["expense"])


async def get_expenses_service(db: AsyncSession = Depends(get_db)) -> ExpensesService:
    return ExpensesService(db)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: UUID,
    user=Depends(get_current_user),
    svc: ExpensesService = Depends(get_expenses_service),
):
    """Delete an expense by ID - matches frontend API contract."""
    success = await svc.delete_expense(expense_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Expense not found")
    return None