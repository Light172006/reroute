# Plan Agent

## Purpose
The Plan Agent constructs day-by-day itineraries tailored to traveler constraints (dates, pace, budget, vibes). It coordinates candidate intake from web research and local catalogs, generates candidate schedules, validates deterministic travel constraints, and commits the initial itinerary version.

## Architecture
- **Framework:** LangGraph `StateGraph`
- **Graph Pipeline:**
  1. `intake`: Unpacks `TripSpec` into the planning state.
  2. `researcher`: Queries place catalog and delegates to the **Web Research Agent** if places for the destination are insufficient.
  3. `planner`: Constructs day-by-day stop assignments using LLM structured generation or deterministic regional scheduling.
  4. `validator`: Evaluates pure-function rules (operating hours, overlaps, drive time limits, high-altitude acclimatization, permits).
  5. `budget_check`: Checks daily and total budget caps.
  6. `finalize`: Persists `version 1` into the itinerary repository.

## Inputs and Outputs
- **Input:**
  - `spec: TripSpec`: Destination, date range, budget, pace, group size, and vibes.
  - `repos: RepositoriesBundle`: Repository access bundle.
- **Output:**
  - Streams typed `AgentEvent`s (`step`, `tool_call`, `tool_result`, `draft`, `done`).
  - Persists initial itinerary `version 1` in `repos.itineraries`.

## Dedicated Tools
- `search_places`: Search catalog places matching city, tags, and category.
- `get_place_details`: Retrieve operational metadata for a specific place.
- `estimate_route`: Calculate driving duration and distance between coordinates.
