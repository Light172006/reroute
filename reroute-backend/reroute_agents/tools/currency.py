"""Currency conversion tool using Frankfurter API with daily caching."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from reroute_agents.repositories.interfaces import CacheRepository
from reroute_agents.tools.base import is_mock_tools, safe_tool


class ConvertCurrencyInput(BaseModel):
    amount: float = Field(description="Monetary amount to convert")
    from_currency: str = Field(default="USD", description="Base currency code (e.g. USD, EUR, INR)")
    to_currency: str = Field(default="INR", description="Target currency code (e.g. INR)")


def create_currency_tool(cache_repo: CacheRepository | None = None) -> Any:
    """Factory creating convert_currency tool."""

    @tool(args_schema=ConvertCurrencyInput)
    @safe_tool(timeout_sec=5.0)
    async def convert_currency(
        amount: float,
        from_currency: str = "USD",
        to_currency: str = "INR",
    ) -> dict[str, Any]:
        """Convert an amount from one currency to another using latest exchange rates."""
        from_cur = from_currency.upper().strip()
        to_cur = to_currency.upper().strip()

        if from_cur == to_cur:
            return {
                "ok": True,
                "amount": amount,
                "converted_amount": amount,
                "rate": 1.0,
                "cached": True,
            }

        today_str = date.today().isoformat()
        cache_key = f"fx:{from_cur}:{to_cur}:{today_str}"

        if cache_repo:
            cached = await cache_repo.get(cache_key)
            if cached and "rate" in cached:
                rate = float(cached["rate"])
                return {
                    "ok": True,
                    "amount": amount,
                    "converted_amount": round(amount * rate, 2),
                    "rate": rate,
                    "cached": True,
                    "source": "frankfurter:cache",
                }

        if is_mock_tools():
            # Standard mock exchange rate USD -> INR ~ 85.0
            mock_rates = {("USD", "INR"): 85.0, ("EUR", "INR"): 92.0, ("GBP", "INR"): 108.0}
            rate = mock_rates.get((from_cur, to_cur), 1.0)
            return {
                "ok": True,
                "amount": amount,
                "converted_amount": round(amount * rate, 2),
                "rate": rate,
                "cached": False,
                "source": "mock_tools",
            }

        # Real Frankfurter API call
        url = f"https://api.frankfurter.app/latest?from={from_cur}&to={to_cur}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            rate = float(data.get("rates", {}).get(to_cur, 1.0))
            if cache_repo:
                await cache_repo.set(cache_key, "frankfurter", {"rate": rate}, ttl_seconds=86400)

            return {
                "ok": True,
                "amount": amount,
                "converted_amount": round(amount * rate, 2),
                "rate": rate,
                "cached": False,
                "source": "frankfurter",
            }
        except Exception:
            # Fallback rate
            fallback_rate = 85.0 if (from_cur == "USD" and to_cur == "INR") else 1.0
            return {
                "ok": True,
                "amount": amount,
                "converted_amount": round(amount * fallback_rate, 2),
                "rate": fallback_rate,
                "cached": False,
                "source": "fallback",
            }

    return convert_currency
