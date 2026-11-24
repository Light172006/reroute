# Chat Agent

## Purpose
The Chat Agent is a conversational ReAct assistant that answers traveler inquiries and assists with itinerary customizations. When the user requests a change (e.g. shift start time, swap a stop), it creates a pending proposal rather than mutating the itinerary directly.

## Architecture
- **Framework:** LangGraph `StateGraph` with ReAct tool execution loop.
- **Graph Nodes:**
  1. `chat_agent`: Evaluates user message, applies system prompt, decides conversational response or tool calls.
  2. `tools`: Executes authorized tools; on item modification, constructs a pending `ReplanProposal`.
  3. `finalize`: Streams token response and emits `done` event.

## Inputs and Outputs
- **Input:**
  - `trip_id: UUID`: Target trip.
  - `messages: list[HumanMessage | AIMessage | ToolMessage]`: Conversation history.
- **Output:**
  - Conversational message response.
  - `proposal: ReplanProposal` when traveler requests an itinerary change.

## Dedicated Tools
- `get_itinerary`: Fetch current stops and schedule.
- `modify_item`: Create modification proposal for traveler review.
- `search_places`: Query catalog places for suggestions.
- `estimate_route`: Compute transit travel time between stops.
- `convert_currency`: Real-time and cached exchange rates.
- `get_expenses_summary`: Trip spending breakdown.

## Safety & Invariants
- **Strict HITL Approval:** Item updates generate pending proposals requiring approval via `interrupt()`.
- **Scope Restriction:** Non-travel inquiries (e.g. general coding, math equations) are politely redirected back to trip management.
