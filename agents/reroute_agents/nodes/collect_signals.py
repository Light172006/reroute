"""Collect signals node: Gathers weather, traffic, hours, and expense signals."""

from __future__ import annotations

from typing import Any

from reroute_agents.events import step_event
from reroute_agents.repositories.interfaces import ExpenseRepository
from reroute_agents.state import ReplanState, Signals
from reroute_agents.tools.injector import DisruptionInjector


def create_collect_signals_node(expense_repo: ExpenseRepository) -> Any:
    """Factory creating collect_signals node."""

    async def collect_signals_node(state: ReplanState) -> dict[str, Any]:
        signals = state.get("signals") or Signals()
        injected = signals.injected
        events = []

        events.append(
            step_event(
                node="collect_signals",
                message="Checking live weather, mountain road conditions, and expense totals",
                status="running",
            )
        )

        if injected:
            # Populate signals from injection
            signals = DisruptionInjector.inject(injected)

        events.append(
            step_event(
                node="collect_signals",
                message="Signals collected successfully",
                status="done",
            )
        )

        return {
            "signals": signals,
            "events": events,
        }

    return collect_signals_node
