# Reroute Backend Integration Notes

This document provides instructions and notes for the backend engineer integrating the `reroute_agents` package into the FastAPI backend.

---

## 1. Package Installation and Import

Per `docs/03_ARCHITECTURE.md`, the backend expects the agent system to be importable as `app.agents` or as an installed package.

### Option A (Recommended for Monorepo): Editable Install
From the repository root:
```bash
pip install -e ./agents
```
Then import directly in FastAPI routers or services:
```python
from reroute_agents.gateway import run_plan, run_replan, resume_replan, run_chat
from reroute_agents.state import TripSpec, InjectedSignals, AgentEvent

# Mount all official agent endpoints directly:
from reroute_agents.api import create_agent_router

agent_router = create_agent_router(repos=backend_repositories_bundle)
app.include_router(agent_router, prefix="/api/v1")
```

### Option B: Direct Package Link
Alternatively, symlink or copy `agents/reroute_agents/` into `reroute-backend/app/agents/`. The package is fully self-contained.

---

## 2. Persistence Boundary and Repositories

The agent layer does not issue direct SQL queries or open raw database connections. Instead, it defines Protocol interfaces in `reroute_agents.repositories.interfaces`:
- `TripRepository`: Fetch trip preferences, dates, metadata.
- `ItineraryRepository`: Fetch and persist itinerary versions and items.
- `ProposalRepository`: Store and query replan proposals.
- `DisruptionRepository`: Record and deduplicate disruptions.
- `PlaceCatalogRepository`: Query curated seed places and cache.
- `ExpenseRepository`: Query logged expenses and summaries.
- `CacheRepository`: Read/write external API responses (`api_cache`).
- `RunEventRepository`: Log agent run events for observability and SSE replay.

### Production Adapter:
The backend services layer should implement these protocols using SQLAlchemy sessions. In `gateway.py`, functions accept an optional `repositories` bundle. If a raw `AsyncSession` is passed (per `docs/05_API_AND_AGENT_CONTRACT.md`), an adapter wraps the session into the repository protocols.

### Checkpointer:
The LangGraph checkpointer is injected. For production, instantiate:
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver(async_connection_pool)
```
For testing and CLI workflows, `langgraph.checkpoint.memory.MemorySaver` is used.

---

## 3. Contract Preservations and Regional Extensions

To strictly preserve `docs/05_API_AND_AGENT_CONTRACT.md` and `docs/04_schema.sql` without breaking changes to top-level fields or enums:

### 3.1 Violation Codes
The contract defines `Violation.code` as:
`Literal["closed", "overlap", "travel_too_long", "over_budget", "day_too_long", "locked_changed"]`

Regional extensions are mapped into these exact codes:
- **Altitude / Acclimatization:** Mapped to code `"day_too_long"`. The `detail` field contains the altitude gain assessment (e.g. `"Altitude gain of 1500m on Day 1 exceeds safe threshold; acclimatization recommended. (Informational guidance, not medical advice)"`).
- **Seasonal Access:** Mapped to code `"closed"`. The `detail` field explains the seasonal closure (e.g. `"Pass closed in winter (December - March)"`).
- **Permit Deadlines:** Mapped to code `"closed"` or flagged in item notes. The `detail` explains permit requirements (e.g. `"Requires Inner Line Permit (ILP); office closed on Sunday"`).

### 3.2 Disruption Types
The database schema enum `disruption_type` is:
`'weather', 'closure', 'hours_conflict', 'delay', 'budget_overrun', 'user_request'`

All Himalayan/NE disruptions map strictly into these types:
- Rain, snowfall, low visibility, high wind -> `'weather'`
- Road/pass closure, permit office closure, attraction closure -> `'closure'`
- Opening hour shifts or check-in mismatches -> `'hours_conflict'`
- Mountain road traffic, landslides, slow transfers -> `'delay'`
- Expense overspend -> `'budget_overrun'`

### 3.3 Replan Decisions
In `docs/05_API_AND_AGENT_CONTRACT.md` Section 3, `resume_replan`'s type hint had `decision: Literal["approve", "reject"]`, while Section 1 of the same doc specified `approve`, `reject`, and `alternatives`.
`reroute_agents.gateway.resume_replan` fully supports all three decisions:
```python
decision: Literal["approve", "reject", "alternatives"]
```
When `alternatives` is passed, the proposal is marked `superseded`, and the agent produces an alternative proposal referencing `alternatives_of`.

---

## 4. Suggested Database Enhancements (Future / Non-Breaking)

The current schema stores extra place attributes inside `places.raw` (JSONB). For performance indexing in future iterations, the backend engineer may consider promoting:
1. `places.altitude_m` (INTEGER NULL): for fast altitude filtering queries.
2. `places.permit_required` (BOOLEAN DEFAULT FALSE): for quick filtering of permit zones.
3. `places.seasonal_access` (JSONB NULL): e.g., `{"open_months": [4, 5, 6, 7, 8, 9, 10]}`.
Until then, `reroute_agents` reads these fields from `places.raw` transparently.

---

## 5. Dependency Pinning and Package Management (AG-004)

Exact pinned versions are maintained in `agents/pyproject.toml` and locked transitively in `agents/requirements.lock` for standalone development, deterministic testing, and CI:
1. `langgraph-checkpoint-postgres` is declared under the `[postgres]` extra (`pip install -e "./agents[postgres]"`).
2. The core agent package avoids imposing postgres drivers when running in offline/in-memory mode or in CLI developer tools.
3. Backend requirements may broaden version ranges if needed for backend framework alignment, but all deterministic agent behaviors and tests have been verified against the exact pins in `agents/requirements.lock`.

---

## 6. Root Cause and Integration Fixes for "Same Results" Across Destinations

During cross-system audit of the bug where selecting "Arunachal Pradesh" and "Sikkim" yielded the same places, the following external root causes were diagnosed:

### 6.1 Frontend Mock Service Worker (MSW) Fixed Return
- **File:** `frontend/src/mocks/handlers.ts:L471`
- **Issue:** When running in mock or offline development mode, the `startGenerate` handler unconditionally returns `days: JSON.parse(JSON.stringify(SEED_DARJEELING_ITINERARY_V1.days))`, ignoring the requested destination in the request payload.
- **Action for Frontend Team:** In `frontend/src/mocks/handlers.ts`, branch on the request destination or load the appropriate regional seed itinerary (`SEED_ARUNACHAL_ITINERARY_V1`, `SEED_SIKKIM_ITINERARY_V1`).

### 6.2 Backend Catalog Repository Unconstrained Fallback
- **File:** `reroute-backend/app/services/agent_repositories.py:L488-L490`
- **Issue:** In `search_places`, if `city` filtering yielded 0 places (e.g. searching for a town or region variant not matching exact DB `city` string), the code executed:
  ```python
  fallback = await self.db.execute(select(Place).limit(limit))
  places = fallback.scalars().all()
  ```
  This pulled the first 30 places from the database regardless of geographical region, which were invariably the initial Darjeeling seed rows.
- **Action for Backend Team:** Remove the unconstrained table fallback. If a destination yields 0 catalog places, delegate to the Web Research Agent or return an empty candidate list rather than returning places from another region.

---

## 7. Frontend SSR / Client Hydration Mismatch in Navbar

### 7.1 Immediate Root Cause
- **File:** `frontend/src/components/Navbar.tsx:L105`
- **Issue:** The landing navigation buttons evaluated `api.isAuthenticated()` directly within the render path. On server-side rendering (Node.js), `api.isAuthenticated()` evaluates to `false` because `localStorage` is not accessible. In the browser client (where tokens may exist in `localStorage`), it evaluates to `true`. This causes the server to output `<a><button>Sign in</button></a>` while the client attempts to hydrate `<a><button><Plus /><svg>Plan a trip</svg></button></a>`, throwing `Error: Hydration failed because the initial UI does not match what was rendered on the server. Expected server HTML to contain a matching <svg> in <button>`.
- **Resolution:** Track authentication state in local React state (`isAuthed`) initialized to `false`, and update it inside `React.useEffect` after component mount (`setMounted(true); setIsAuthed(api.isAuthenticated())`). Guard rendering with `!mounted || (isLanding && !isAuthed)` so server HTML and initial client render match identically.

