"""Permit verification and documentation rules for regulated border regions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from reroute_agents.state import DraftItem, Violation

PERMIT_VERIFY_DISCLAIMER = (
    "Permit requirements change; verify with official government sources before travel."
)


def check_permits(
    items_by_day: dict[int, list[DraftItem]],
    places_metadata: dict[UUID, dict[str, Any]],
) -> tuple[list[Violation], list[str]]:
    """Inspect places for permit requirements (ILP, PAP, RAP).

    Returns:
    - List of violations (e.g. if permit notes indicate closure or unavailable processing day)
    - List of informational permit summaries for the trip.
    """
    violations: list[Violation] = []
    permit_summaries: list[str] = []
    seen_permits: set[str] = set()

    for day_index, day_items in items_by_day.items():
        for item in day_items:
            if not item.place_id or item.place_id not in places_metadata:
                continue

            meta = places_metadata[item.place_id]
            raw = meta.get("raw", {})
            permit_required = raw.get("permit_required", False) or meta.get(
                "permit_required", False
            )
            permit_notes = raw.get("permit_notes") or meta.get("permit_notes")

            if permit_required:
                note_text = permit_notes or f"Permit required for {item.title}."
                if note_text not in seen_permits:
                    seen_permits.add(note_text)
                    permit_summaries.append(
                        f"{item.title}: {note_text} ({PERMIT_VERIFY_DISCLAIMER})"
                    )

                # If item notes do not mention permit, annotate item notes
                if item.notes:
                    if "permit" not in item.notes.lower():
                        item.notes = (
                            f"{item.notes} | Notice: {note_text} ({PERMIT_VERIFY_DISCLAIMER})"
                        )
                else:
                    item.notes = f"Notice: {note_text} ({PERMIT_VERIFY_DISCLAIMER})"

                # If place metadata marks permit office closed or unavailable
                if raw.get("permit_office_closed", False):
                    violations.append(
                        Violation(
                            code="closed",
                            day_index=day_index,
                            item_stable_key=item.stable_key,
                            detail=f"Permit office closed for {item.title}. Cannot issue access permit. {PERMIT_VERIFY_DISCLAIMER}",
                        )
                    )

    return violations, permit_summaries
