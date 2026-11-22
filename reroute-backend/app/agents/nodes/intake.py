"""Intake node: parses user preferences into a TripSpec."""
from __future__ import annotations

from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.state import PlanState, TripSpec


class IntakeOutput(BaseModel):
    """Structured output for intake node."""
    destination: str = Field(description="Destination city")
    start_date: str = Field(description="Start date (YYYY-MM-DD)")
    end_date: str = Field(description="End date (YYYY-MM-DD)")
    group_size: int = Field(description="Number of travelers", ge=1)
    budget_total: float = Field(description="Total budget in trip currency")
    currency: str = Field(description="Currency code (e.g., INR)")
    pace: str = Field(description="Pace: relaxed, balanced, or packed")
    vibe_tags: list[str] = Field(description="Vibe tags like food, nature, culture")
    notes: Optional[str] = Field(default=None, description="Additional notes")


SYSTEM_PROMPT = """You are a travel intake specialist. Parse the user's trip request into a structured TripSpec.
Extract: destination city, dates, group size, budget, currency, pace, and vibe tags.
If any field is missing, make reasonable defaults.
Return ONLY the JSON object matching the schema."""


def intake(llm: Optional[BaseChatModel] = None):
    """Create the intake node function."""
    async def _node(state: PlanState) -> PlanState:
        spec = state.get("spec", {})
        # If spec is already complete, just pass through
        if all(k in spec for k in ("destination", "start_date", "end_date", "budget_total")):
            return {"spec": spec, "message": "TripSpec already complete"}

        # Otherwise use LLM to extract from user input
        if llm:
            try:
                structured_llm = llm.with_structured_output(IntakeOutput)
                # In real use, user input would be in state["user_input"]
                # For now, use the spec as context
                prompt = f"Trip preferences: {spec}"
                result = await structured_llm.ainvoke([
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=prompt)
                ])
                spec = result.model_dump()
            except Exception:
                # Fall back to spec as-is
                pass

        return {"spec": spec, "message": "TripSpec normalized"}

    return _node