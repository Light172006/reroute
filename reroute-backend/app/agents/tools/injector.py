"""Disruption injector for demo mode.

Allows /demo/simulate to inject signals that the replan graph picks up.
"""
from __future__ import annotations

from app.agents.tools.weather import _INJECTED as _WEATHER_INJECTED, inject_forecast


class DisruptionInjector:
    """Manages injected disruptions for demo mode."""

    @staticmethod
    def inject_weather(city: str, day_index: int, precip_prob: int, window: str = "14-18h") -> None:
        """Inject a weather disruption."""
        inject_forecast(city, day_index, precip_prob, window)

    @staticmethod
    def inject_closure(place_id: str, day_index: int, reason: str = "temporarily closed") -> None:
        """Inject a closure disruption (stored differently in real impl)."""
        # In mock mode, we just use the weather injector with a special key
        _WEATHER_INJECTED[(f"closure:{place_id}", day_index)] = {"type": "closure", "reason": reason}

    @staticmethod
    def clear_all() -> None:
        """Clear all injected disruptions."""
        _WEATHER_INJECTED.clear()