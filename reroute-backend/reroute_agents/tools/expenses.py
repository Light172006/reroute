"""Expense tracking and budget summary tool."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from reroute_agents.repositories.interfaces import ExpenseRepository
from reroute_agents.tools.base import safe_tool


class ExpensesSummaryInput(BaseModel):
    trip_id: str = Field(description="UUID string of the trip to summarize expenses for")


def create_expenses_tool(expense_repo: ExpenseRepository) -> Any:
    """Factory creating get_expenses_summary tool."""

    @tool(args_schema=ExpensesSummaryInput)
    @safe_tool(timeout_sec=5.0)
    async def get_expenses_summary(trip_id: str) -> dict[str, Any]:
        """Fetch total actual expenses and breakdown by category for a trip."""
        try:
            t_uuid = UUID(trip_id)
        except ValueError:
            return {"ok": False, "error": f"Invalid UUID: {trip_id}"}

        summary = await expense_repo.get_expenses_summary(t_uuid)
        return {
            "ok": True,
            "trip_id": trip_id,
            "summary": summary,
        }

    return get_expenses_summary
