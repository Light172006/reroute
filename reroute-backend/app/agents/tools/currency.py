"""Currency conversion tool with mock mode."""
from __future__ import annotations

import logging

from langchain_core.tools import tool

from app.core.config import settings

log = logging.getLogger("reroute.tools.currency")

# Mock rates (base: INR)
MOCK_RATES = {
    "USD": 0.012,
    "EUR": 0.011,
    "GBP": 0.0095,
    "JPY": 1.8,
    "INR": 1.0,
}


@tool(args_schema=None)
def convert_currency(amount: float, from_currency: str = "INR", to_currency: str = "USD") -> dict:
    """Convert amount from one currency to another."""
    if getattr(settings, "MOCK_TOOLS", True):
        from_rate = MOCK_RATES.get(from_currency.upper(), 1.0)
        to_rate = MOCK_RATES.get(to_currency.upper(), 1.0)
        # Convert via INR as base
        inr_amount = amount / from_rate
        result = inr_amount * to_rate
        return {"ok": True, "source": "mock", "converted": round(result, 2), "rate": round(to_rate / from_rate, 6)}

    # Real implementation: exchange rate API
    return {"ok": False, "error": "Real currency conversion not implemented"}