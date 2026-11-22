"""Expense tracking tool."""
from __future__ import annotations

import logging

from langchain_core.tools import tool

from app.core.config import settings

log = logging.getLogger("reroute.tools.expenses")


@tool(args_schema=None)
def add_expense(trip_id: str, category: str, amount: float, currency: str = "INR",
                description: str = "", item_stable_key: str = "") -> dict:
    """Record an expense for a trip.

    In a real implementation, this would write to the expenses table.
    """
    if getattr(settings, "MOCK_TOOLS", True):
        return {"ok": True, "source": "mock", "expense_id": "mock-expense-id"}

    return {"ok": False, "error": "Real expense tracking not implemented"}