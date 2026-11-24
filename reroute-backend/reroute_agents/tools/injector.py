"""Disruption Injector: Generates synthetic real-world disruptions for simulation and testing."""

from __future__ import annotations

from typing import Any

from reroute_agents.state import InjectedSignals, Signals


class DisruptionInjector:
    """Transforms an InjectedSignals specification into populated Signals for the replan pipeline."""

    @staticmethod
    def inject(injected: InjectedSignals) -> Signals:
        """Create a synthetic Signals bundle based on injected parameters."""
        signals = Signals(injected=injected)

        if injected.type == "weather":
            precip = float(injected.params.get("precip_prob", 0.85))
            snow = float(injected.params.get("snowfall", 0.0))
            vis = int(injected.params.get("visibility", 10000))
            from_h = int(str(injected.params.get("from", "13:00")).split(":")[0])
            to_h = int(str(injected.params.get("to", "17:00")).split(":")[0])

            hourly: list[dict[str, Any]] = []
            for h in range(24):
                if from_h <= h <= to_h:
                    hourly.append(
                        {
                            "hour": h,
                            "precip_prob": precip,
                            "snowfall": snow,
                            "visibility": vis,
                        }
                    )
                else:
                    hourly.append(
                        {
                            "hour": h,
                            "precip_prob": 0.05,
                            "snowfall": 0.0,
                            "visibility": 10000,
                        }
                    )

            signals.weather_forecast = {str(injected.day_index): {"hourly": hourly}}

        elif injected.type == "closure":
            place_id = injected.params.get("place_id")
            reason = injected.params.get("reason", "Unexpected road or attraction closure")
            if place_id:
                signals.opening_hours_updates = {
                    str(place_id): {"is_closed": True, "reason": reason}
                }

        elif injected.type == "delay":
            delay_min = int(injected.params.get("delay_minutes", 45))
            signals.travel_estimates = {
                "legs": [
                    {
                        "day_index": injected.day_index,
                        "leg_index": 1,
                        "planned_minutes": 30,
                        "new_minutes": 30 + delay_min,
                    }
                ]
            }

        elif injected.type == "budget_overrun":
            # Actual spending higher than planned
            overrun_pct = float(injected.params.get("overrun_pct", 0.15))
            signals.expenses_summary = {
                "overrun_pct": overrun_pct,
                "total": 12000 * (1.0 + overrun_pct),
            }

        return signals


def create_injector_tool() -> Any:
    """Create LangChain BaseTool for disruption injection."""
    from langchain_core.tools import tool

    @tool
    def inject_disruption(
        type: str, day_index: int, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Inject a synthetic disruption signal (weather, closure, delay, budget_overrun) for testing."""
        injected = InjectedSignals(
            type=type,  # type: ignore[arg-type]
            day_index=day_index,
            params=params or {},
        )
        signals = DisruptionInjector.inject(injected)
        return {"ok": True, "type": type, "day_index": day_index, "signals": signals.model_dump()}

    return inject_disruption
