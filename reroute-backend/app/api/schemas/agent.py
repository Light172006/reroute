# app/api/schemas/agent.py
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Empty for now; idempotency key comes from header."""
    pass


class CheckRequest(BaseModel):
    """Empty for now; manual check just triggers replan."""
    pass


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class ProposalDecisionRequest(BaseModel):
    decision: str  # "approve" | "reject" | "alternatives"
    note: Optional[str] = None


class SimulateRequest(BaseModel):
    trip_id: Optional[uuid.UUID] = None
    type: str = "weather"
    day_index: int = 1
    params: Optional[dict] = None
