# Replan Agent

## Purpose
The Replan Agent monitors itineraries for active real-world disruptions (landslides, severe weather, road/pass closures, transit delays, budget overruns), computes physical impacts, and crafts targeted repair proposals for human approval.

## Architecture
- **Framework:** LangGraph `StateGraph`
- **Graph Pipeline:**
  1. `collect_signals`: Ingests weather forecasts and expense updates.
  2. `impact_analyzer`: Identifies affected itinerary stops using pure-function impact rules.
  3. `replanner`: Proposes replacement stops (preferring cached research before making bounded web calls).
  4. `validator`: Ensures proposed replacements satisfy operating hours and travel constraints.
  5. `build_proposal`: Calculates diffs, creates `ReplanProposal`, and executes `interrupt()` for human approval.
  6. `apply_changes`: Commits approved proposal to database as a new version.

## Inputs and Outputs
- **Input:**
  - `trip_id: UUID`: Target trip.
  - `signals: Signals`: Ingested disruption signals.
- **Output:**
  - `ReplanProposal`: Diff of proposed additions, removals, or shifts.
  - Interrupt for user decision (`approve`, `reject`, `alternatives`).

## Dedicated Tools
- `weather_forecast`: Query Open-Meteo or mock forecasts.
- `inject_disruption`: Test signal injector.
- `search_places`: Catalog candidate queries for replacement stops.

## Safety & Invariants
- **Human-in-the-Loop:** Changes are NEVER directly written without user approval.
- **Locked Items:** Stops flagged as `is_locked=True` are strictly protected and never modified.
