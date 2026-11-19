# Reroute: System Architecture

Stack: **FastAPI** (API), **LangChain + LangGraph** (agents), **PostgreSQL** (data + LangGraph checkpoints), **Redis** (cache, optional), **Next.js** (frontend).

---

## 1. High-Level Diagram

```
+-------------------+        HTTPS / SSE         +----------------------------+
|  Next.js Frontend | <------------------------> |        FastAPI Backend     |
|  (React, Tailwind)|                            |  - REST routers            |
+-------------------+                            |  - SSE streaming           |
                                                 |  - Auth (JWT)              |
                                                 |  - Services layer          |
                                                 +-----+----------------+-----+
                                                       |                |
                                       +---------------+                +-----------------+
                                       v                                                  v
                        +-----------------------------+                    +---------------------------+
                        |     Agent Runtime           |                    |   PostgreSQL              |
                        |  LangGraph graphs           |  <---------------> |  app tables + checkpoints |
                        |  - plan_graph               |   state/persist    +---------------------------+
                        |  - replan_graph             |                    +---------------------------+
                        |  - chat_graph               |  <---------------> |   Redis (cache, locks)    |
                        +--------------+--------------+                    +---------------------------+
                                       |
                +----------------------+-----------------------+
                v                      v                       v
        +--------------+     +------------------+     +---------------------+
        | LLM Gateway  |     |   Tool Layer     |     |  Monitor Worker     |
        | (LiteLLM /   |     | places, weather, |     |  (APScheduler /     |
        | init_chat_   |     | routing, currency|     |  background task)   |
        | model +      |     | (cached, retried)|     |  triggers replan    |
        | fallbacks)   |     +--------+---------+     +---------------------+
        +------+-------+              |
               v                      v
     Gemini/Groq/OpenRouter     Open-Meteo, OSM/Overpass,
     Ollama (local fallback)    OpenRouteService, Frankfurter
```

## 2. Components

### 2.1 Frontend (Next.js)
- Talks only to FastAPI. Consumes REST + SSE.
- Never calls LLMs or third-party APIs directly.

### 2.2 FastAPI Backend
- **Routers:** `auth`, `trips`, `itineraries`, `proposals`, `expenses`, `agent`, `demo`.
- **Services layer:** business logic (versioning, applying proposals, diffing). Routers stay thin.
- **Agent gateway:** the only module that imports LangGraph. Exposes `run_plan()`, `run_replan()`, `run_chat()` as async generators yielding typed events.
- **SSE:** `StreamingResponse` / `sse-starlette`, forwarding agent events.
- **Background monitor:** APScheduler job (or manual `POST /trips/{id}/check`) that evaluates active trips.

### 2.3 Agent Runtime (LangGraph)

Three graphs share tools and state schemas.

#### A. `plan_graph` (initial itinerary)

```
START -> intake -> researcher -> planner -> validator --(ok)--> budget_check --(ok)--> finalize -> END
                                    ^           |                    |
                                    +-- fix ----+--(violations)      +--(over budget)--> planner
                                    (max 3 loops, then finalize with flagged issues)
```

| Node | Responsibility | Model tier |
|---|---|---|
| `intake` | Normalize preferences into structured `TripSpec` | small |
| `researcher` | Tool calls: candidate places, hours, coordinates, costs | small/medium (tool-calling) |
| `planner` | Build day-wise schedule as structured output (`ItineraryDraft`) | strong |
| `validator` | **Deterministic code** (no LLM): checks hours, travel time, daily limits, locked items | none |
| `budget_check` | Sum costs vs budget, produce a violation report | none (code) |
| `finalize` | Persist itinerary version, emit summary | small |

#### B. `replan_graph` (the differentiator)

```
START -> collect_signals -> impact_analyzer --(no impact)--> END
                                  |
                                  v
                              replanner -> validator -> (loop <=2) -> build_proposal
                                                                           |
                                                                    interrupt() [HITL]
                                                                           |
                                                          approved -> apply_changes -> END
                                                          rejected -> END
```

| Node | Responsibility |
|---|---|
| `collect_signals` | Weather forecast, re-check hours, travel estimates, expense totals |
| `impact_analyzer` | **Code first**: rules detect affected items (outdoor + rain > 60%, opening-hours conflict, delay, budget overrun). Outputs `DisruptionEvent[]` |
| `replanner` | LLM proposes substitutions **only for affected items**; locked items excluded; uses researcher tools for alternatives |
| `validator` | Same deterministic validator as `plan_graph` |
| `build_proposal` | Creates diff (before/after), reason, cost/time impact; saves `replan_proposals` row |
| `interrupt()` | LangGraph human-in-the-loop pause; resumes when the user approves or rejects via API |
| `apply_changes` | Writes new itinerary version |

#### C. `chat_graph`
A ReAct-style agent (`create_react_agent` or custom) with tools: `get_itinerary`, `modify_item`, `search_places`, `estimate_route`. Any modification goes through the proposal flow (no silent edits).

### 2.4 State (LangGraph TypedDict / Pydantic)

```python
class PlanState(TypedDict):
    trip_id: str
    spec: TripSpec                  # destination, dates, budget, vibe tags, pace
    candidates: list[PlaceCandidate]
    draft: ItineraryDraft | None
    violations: list[Violation]
    iteration: int
    events: Annotated[list[AgentEvent], add]   # streamed to client

class ReplanState(TypedDict):
    trip_id: str
    base_version_id: str
    signals: Signals
    disruptions: list[DisruptionEvent]
    affected_item_ids: list[str]
    proposal: ReplanProposal | None
    decision: Literal["approve", "reject", "alternatives"] | None
    iteration: int
```

- **Checkpointer:** `langgraph-checkpoint-postgres` (`PostgresSaver` / `AsyncPostgresSaver`). `thread_id = run_id`. This enables `interrupt()` resume across requests and restarts.

### 2.5 LLM Gateway
- One module: `get_llm(tier: "small"|"strong"|"local")`.
- Config-driven model chain per tier with fallbacks (e.g. Gemini free -> Groq -> Ollama).
- Use `.with_structured_output(PydanticModel)` for all structured steps; retry once on parse failure.
- Per-user and global rate limiting, token/latency logging into `agent_run_events`.

### 2.6 Tool Layer
All tools are LangChain `@tool` functions with Pydantic arg schemas, wrapped with: **timeout, retry (tenacity), cache (Redis/DB `api_cache`), error normalization** (`{"ok": false, "error": "..."}` rather than exceptions).

| Tool | Source (free) | Notes |
|---|---|---|
| `search_places` | OpenStreetMap Overpass / Nominatim (or Geoapify free tier) | Seed curated JSON for demo cities as primary |
| `get_place_details` | Seed data + OSM tags | opening hours, category, indoor/outdoor, avg cost, coords |
| `get_weather_forecast` | Open-Meteo (no key) | hourly precip probability |
| `estimate_route` | OpenRouteService (free key) or OSRM | travel minutes + distance by mode |
| `convert_currency` | Frankfurter API | cached daily |
| `get_expenses_summary` | internal DB | planned vs actual |

**Demo-safe design:** every tool supports a `mock` mode and a `DisruptionInjector` that returns forced data (rain, closure, delay) for `POST /demo/simulate`.

### 2.7 Monitor Worker
- APScheduler (in-process for v1) runs every N minutes for trips with `status = active|planned` and start date within 7 days.
- Cheap rules run first; the LLM is invoked only if a rule fires. Prevents wasting free-tier quota.
- Dedup via `disruption_events.fingerprint` so the same issue isn't proposed twice.

## 3. Key Flows

### 3.1 Create and generate
1. `POST /trips` -> trip row (draft).
2. `POST /trips/{id}/generate` -> creates `agent_runs` row, returns `run_id`.
3. `GET /agent/runs/{run_id}/stream` (SSE) -> events: `step`, `tool_call`, `draft`, `done`.
4. `finalize` saves `itinerary_versions` + items; frontend refetches `GET /trips/{id}/itinerary`.

### 3.2 Disruption -> replan -> approval
1. Monitor/`POST /trips/{id}/check` starts `replan_graph` (`run_id`).
2. Graph builds a proposal and calls `interrupt()`; run status becomes `awaiting_user`.
3. Frontend shows the banner and calls `GET /proposals/{id}`.
4. User clicks Approve -> `POST /proposals/{id}/decision {decision: "approve"}`.
5. Backend resumes the graph with `Command(resume={"decision": "approve"})` -> `apply_changes` -> new `itinerary_versions` row (`parent_version_id`, `reason`).
6. SSE `done` event; frontend refreshes.

### 3.3 Demo simulation
`POST /demo/simulate {trip_id, type: "rain", day: 2}` -> injects a synthetic `Signals` into `collect_signals` -> same pipeline as 3.2.

## 4. Backend Project Structure

```
reroute-backend/
  app/
    main.py
    core/            config.py, security.py, logging.py, deps.py
    api/
      routers/       auth.py trips.py itinerary.py proposals.py expenses.py agent.py demo.py
      schemas/       pydantic request/response models (shared with agent state types)
    db/
      session.py  models.py  (SQLAlchemy 2.0)  repositories/
    services/        trip_service.py itinerary_service.py proposal_service.py diff.py
    agents/
      gateway.py     run_plan / run_replan / run_chat (async generators of events)
      llm.py         get_llm(tier) with fallbacks
      state.py       TripSpec, ItineraryDraft, Signals, DisruptionEvent, ...
      graphs/        plan_graph.py replan_graph.py chat_graph.py
      nodes/         intake.py researcher.py planner.py validator.py impact.py replanner.py ...
      tools/         places.py weather.py routing.py currency.py expenses.py injector.py
      prompts/       *.md
    workers/         monitor.py
  migrations/        (Alembic)
  tests/             unit (validator, impact rules), graph tests (mock LLM), API tests
  data/seed/         curated places for demo cities (json)
  docker-compose.yml  .env.example
```

## 5. Integration Contract Between Agent and API (Backend Engineer Notes)

- Agents **never** write directly to HTTP; they yield `AgentEvent` objects. The API layer maps events to SSE and DB logs.
- Agents **do** persist domain data through the services layer (not raw SQL) so versioning logic stays in one place.
- One `run_id` = one LangGraph `thread_id` = one `agent_runs` row.
- All agent inputs/outputs are Pydantic models defined in `agents/state.py` and re-exported to `api/schemas` so frontend and agents share the same shapes (generate TypeScript types from OpenAPI).
- The validator and impact analyzer are pure functions with unit tests. They are the source of truth for "is the plan valid", **not** the LLM.
- Idempotency: `POST /trips/{id}/generate` and `/check` accept an `Idempotency-Key` header; only one active run per trip.

## 6. Non-Functional Design

| Concern | Approach |
|---|---|
| Rate limits | Token bucket per user; cache tool results; small model for cheap nodes |
| Failover | LLM chain with fallback; tool errors return structured failures |
| Observability | Log each node/tool/LLM call to `agent_run_events` (latency, tokens, model); optional LangSmith tracing |
| Security | JWT (access + refresh), password hashing (argon2/bcrypt), row-level ownership checks, CORS allowlist, secrets via env |
| Testing | Fake LLM for graph tests; golden test set of 20 trips + 10 disruptions; validator property tests |
| Deployment | Docker Compose (api, postgres, redis); frontend on Vercel; backend on Render/Railway/Fly free tier |

## 7. Environment Variables (`.env.example`)

```
DATABASE_URL=postgresql+asyncpg://reroute:reroute@db:5432/reroute
REDIS_URL=redis://redis:6379/0
JWT_SECRET=change-me
LLM_STRONG_CHAIN=gemini:gemini-2.5-flash,groq:llama-3.3-70b-versatile
LLM_SMALL_CHAIN=groq:llama-3.1-8b-instant,ollama:qwen3:4b
GOOGLE_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=
ORS_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
MOCK_TOOLS=false
LANGSMITH_TRACING=false
```
(Model names are examples; confirm current free-tier availability and limits before choosing.)

## 8. Build Order (for the backend engineer)

1. DB + migrations + auth + trip CRUD.
2. Agent gateway with a **fake** plan graph that streams canned events (unblocks frontend immediately).
3. Tool layer with mock mode + seed data.
4. Real `plan_graph` + validator.
5. `replan_graph` + checkpointer + `interrupt()` + proposal endpoints.
6. Monitor worker + demo injector.
7. Chat graph, expenses, polish, evaluation set.
