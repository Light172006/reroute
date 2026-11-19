# Reroute: Product Requirements Document (PRD)

**Version:** 1.0 | **Status:** Draft for team review | **Project type:** IDP (agentic AI travel app)

---

## 1. Overview

**Reroute** is an agentic AI travel planner that builds an itinerary and then *keeps watching it*. When the real world changes (rain, a closed attraction, a delayed train, a blown budget), Reroute detects the impact, rewrites only the affected part of the plan, and explains why. The user approves or rejects the change.

**One-line pitch:** "A trip plan that fixes itself."

## 2. Problem

- Static itineraries break the moment reality differs from the plan.
- Travelers re-plan manually under stress, across 5+ apps (maps, weather, booking, notes).
- Existing AI planners generate a plan once and stop. They do not monitor or adapt.

## 3. Goals and Non-Goals

### Goals
1. Generate a feasible day-by-day itinerary from preferences (destination, dates, budget, vibe).
2. Monitor the plan against live signals (weather, opening hours, travel time, budget burn).
3. Automatically propose minimal replans with a clear explanation.
4. Keep the user in control: no change is applied without approval (human-in-the-loop).

### Non-Goals (v1)
- Real booking or payments (mock or deep-link only).
- Multi-city or international visa planning.
- Group/collab planning (future scope).
- Native mobile apps (responsive web only).

## 4. Target Users

| Persona | Description | Key need |
|---|---|---|
| **Aarav, student backpacker** | 20-24, tight budget, travels in small groups | Cheap plans that survive surprises |
| **Meera, weekend traveler** | 25-35, time-poor, 2-3 day trips | Fast plan, less stress when things change |

## 5. Scope (v1 Vertical Slice)

- **Destination coverage:** a limited set of cities (e.g. Kolkata, Darjeeling, Goa, Jaipur). Seed and cache data for these.
- **Agents:** Planner, Researcher, Budget Tracker, Replanner (+ Validator node).
- **Signals:** weather, opening hours, travel time, budget.
- **Platform:** responsive web app.

## 6. User Stories and Acceptance Criteria

### Epic A: Trip creation
- **A1.** As a user, I can enter destination, dates, budget, group size, and vibe tags (food, culture, nature, nightlife, relaxed/packed).
  *AC:* Form validates; trip saved as `draft`.
- **A2.** As a user, I can see an itinerary generated within ~60s with streaming progress.
  *AC:* Itinerary has day-wise items with times, locations, cost estimates, and travel time between stops. Total cost <= budget (or flagged).
- **A3.** As a user, I can edit, remove, lock, or reorder items.
  *AC:* Locked items are never changed by the Replanner.

### Epic B: Monitoring and replanning (core differentiator)
- **B1.** The system checks the trip for disruptions on a schedule and on demand ("Check my plan now").
  *AC:* Detects at least: rain on outdoor items, closed/opening-hours conflict, travel delay > threshold, budget overrun.
- **B2.** On a disruption, the Replanner produces a **proposal** that modifies only affected items.
  *AC:* Proposal shows a before/after diff, reason, and cost/time impact.
- **B3.** User can approve, reject, or ask for alternatives.
  *AC:* Approve creates a new itinerary version; reject keeps the current one; full history kept.
- **B4.** User can simulate a disruption (demo mode: "Simulate rain on Day 2").
  *AC:* Triggers the same pipeline with injected event data.

### Epic C: Budget
- **C1.** User can log expenses; the Budget Tracker shows planned vs actual.
  *AC:* Overrun beyond 10% raises a budget disruption event.

### Epic D: Explainability
- **D1.** Every agent action shows in an activity timeline ("Checked weather", "Found 3 indoor alternatives").
  *AC:* Streamed live and stored per run.

## 7. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Auth (email/password or Google OAuth) | P0 |
| FR-2 | Create/read/update/delete trips | P0 |
| FR-3 | Agentic itinerary generation with streaming | P0 |
| FR-4 | Constraint validation (budget, opening hours, travel time, daily time limit) | P0 |
| FR-5 | Disruption detection (weather, hours, delay, budget) | P0 |
| FR-6 | Replan proposal + approve/reject (HITL) | P0 |
| FR-7 | Itinerary versioning and diff | P1 |
| FR-8 | Chat panel to talk to the agent ("make Day 2 more relaxed") | P1 |
| FR-9 | Expense logging | P1 |
| FR-10 | Map view of day route | P1 |
| FR-11 | Export/share itinerary (PDF/link) | P2 |
| FR-12 | Local model fallback (Ollama) | P2 |

## 8. Non-Functional Requirements

- **Latency:** initial plan <= 60s p90; replan proposal <= 20s p90.
- **Reliability:** LLM provider failover (primary -> fallback -> local). Tool failures degrade gracefully (cached data, clear message).
- **Cost:** must run on free-tier APIs; cache aggressively; rate-limit per user.
- **Safety:** no auto-applied changes; mock all payment actions; never store secrets in the DB.
- **Observability:** every agent run and tool call logged (see `agent_runs`, `agent_run_events`).
- **Security:** JWT auth, per-user data isolation, input validation, CORS allowlist.

## 9. Success Metrics (for demo/evaluation)

| Metric | Target |
|---|---|
| Constraint satisfaction on test trips (budget, hours, time) | >= 90% |
| Replan proposals that touch only affected items | >= 85% |
| Plan generation success rate | >= 95% |
| Median plan generation time | <= 40s |
| Test set | 20 scripted trips + 10 disruption scenarios |

## 10. Key Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Free LLM rate limits / outages | Model abstraction layer, fallback chain, response caching |
| Weak tool-calling in small models | Use structured outputs (Pydantic), strong model for planner, validator loop |
| Place/hours data incomplete | Seed curated data for demo cities, cache, mark confidence level |
| Scope creep | Hold to v1 vertical slice; P2 items only if time remains |
| Demo-day failures | Demo mode with injected events; pre-cached trips; local fallback |

## 11. Milestones (suggested 6 weeks)

| Week | Deliverable |
|---|---|
| 1 | Specs frozen, repo set up, DB + auth + trip CRUD, mock agent endpoint |
| 2 | Researcher + tool layer (places, weather, routing), caching |
| 3 | Planner + Validator graph, streaming to UI |
| 4 | Monitor + Replanner + proposal/approve flow |
| 5 | Budget tracker, chat panel, versioning/diff, map view |
| 6 | Evaluation set, polish, demo mode, documentation |

## 12. Open Questions

1. Which cities are in the v1 seed set?
2. Which LLM providers will the team use as primary and fallback?
3. Is a scheduled background monitor required, or is on-demand check enough for the demo?
