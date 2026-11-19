# Reroute: API and Agent Integration Contract

Single source of truth for **frontend <-> FastAPI <-> LangGraph agents**. Base path: `/api/v1`. Auth: `Authorization: Bearer <JWT>` on everything except `/auth/*`.
All IDs are UUIDs. Times are ISO-8601; item times are local `HH:MM` for the trip's destination.

---

## 1. REST Endpoints

### Auth
| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/auth/signup` | `{email, password, display_name}` | `{access_token, refresh_token, user}` |
| POST | `/auth/login` | `{email, password}` | same |
| POST | `/auth/refresh` | `{refresh_token}` | `{access_token}` |
| GET | `/me` | | `User` |

### Trips
| Method | Path | Notes |
|---|---|---|
| POST | `/trips` | Create (status `draft`) |
| GET | `/trips` | List mine; includes `has_pending_proposal: bool` |
| GET | `/trips/{id}` | Trip + `current_version_id` |
| PATCH | `/trips/{id}` | Edit preferences |
| DELETE | `/trips/{id}` | Archive/delete |

`TripCreate`:
```json
{
  "title": "Darjeeling weekend",
  "destination": "Darjeeling",
  "start_date": "2026-12-12",
  "end_date": "2026-12-14",
  "group_size": 3,
  "budget_total": 15000,
  "budget_per_day_cap": null,
  "currency": "INR",
  "pace": "balanced",
  "vibe_tags": ["food", "nature"],
  "notes": "Vegetarian friendly"
}
```

### Itinerary
| Method | Path | Notes |
|---|---|---|
| GET | `/trips/{id}/itinerary` | Current version with items grouped by day |
| GET | `/trips/{id}/versions` | List versions |
| GET | `/trips/{id}/versions/{version_id}` | Specific version |
| GET | `/trips/{id}/versions/diff?from=&to=` | Diff between versions (matched by `stable_key`) |
| POST | `/trips/{id}/versions/{version_id}/restore` | Creates a new version copying the old one |
| PATCH | `/items/{item_id}` | Manual edit: `{is_locked?, start_time?, end_time?, notes?}` (creates new version `created_by: user`) |
| DELETE | `/items/{item_id}` | Remove (creates new version) |
| POST | `/trips/{id}/items/reorder` | `{day_index, ordered_stable_keys[]}` |

`ItineraryResponse`:
```json
{
  "trip_id": "...",
  "version": {"id": "...", "version_no": 2, "reason": "Rain replan, Day 2", "created_by": "agent:replanner", "total_cost": 12400, "created_at": "..."},
  "days": [
    {
      "day_index": 1,
      "date": "2026-12-12",
      "summary": {"cost": 3200, "walking_min": 55, "active_min": 480},
      "items": [
        {
          "id": "...", "stable_key": "...", "position": 0,
          "title": "Batasia Loop", "category": "sightseeing", "setting": "outdoor",
          "start_time": "09:00", "end_time": "10:30", "est_cost": 150,
          "lat": 27.03, "lng": 88.26, "is_locked": false, "flags": ["weather_risk"],
          "travel": {"mode": "taxi", "minutes": 15, "distance_m": 4200},
          "place_id": "...", "notes": null
        }
      ]
    }
  ]
}
```

### Agent runs
| Method | Path | Notes |
|---|---|---|
| POST | `/trips/{id}/generate` | Starts `plan_graph`. Header `Idempotency-Key` optional. Returns `{run_id}` (202) |
| POST | `/trips/{id}/check` | Starts `replan_graph` ("Check my plan now"). Returns `{run_id}` (202) |
| POST | `/trips/{id}/chat` | `{message}` -> starts `chat_graph`. Returns `{run_id, message_id}` |
| GET | `/agent/runs/{run_id}` | Status + output |
| GET | `/agent/runs/{run_id}/stream` | **SSE** stream (see section 2). Supports `Last-Event-ID` for resume |
| POST | `/agent/runs/{run_id}/cancel` | Cancel |
| GET | `/trips/{id}/chat` | Chat history |

Errors: `409` if the trip already has an active run (`{"detail":"run_in_progress","run_id":"..."}`).

### Proposals (human-in-the-loop)
| Method | Path | Notes |
|---|---|---|
| GET | `/trips/{id}/proposals?status=pending` | List |
| GET | `/proposals/{id}` | Full proposal with diff |
| POST | `/proposals/{id}/decision` | `{decision: "approve"|"reject"|"alternatives", note?}` |

`decision` behavior:
- `approve` -> resumes the graph, applies changes, new version created. Returns `{status:"approved", version_id}`.
- `reject` -> proposal `rejected`, graph ends. Returns `{status:"rejected"}`.
- `alternatives` -> proposal `superseded`; a new run produces another proposal (`alternatives_of`). Returns `{run_id}`; frontend opens the stream.

`ProposalResponse`:
```json
{
  "id": "...", "status": "pending",
  "reason": "Rain likely on Day 2 (80%, 14:00-18:00)",
  "explanation": "Swapped 2 outdoor stops for indoor ones within 1.2 km, keeping total cost under budget.",
  "disruptions": [{"id":"...","type":"weather","severity":"high","day_index":2,"summary":"Rain 80% 2-6pm","source":"open-meteo"}],
  "cost_delta": -150, "time_delta_min": 10, "items_changed": 2,
  "diff": [
    {"op":"replace","day":2,"stable_key":"...",
     "before":{"title":"Tiger Hill walk","start":"14:00","end":"16:00","cost":200},
     "after":{"title":"Tibetan Refugee Self-Help Centre","start":"14:00","end":"16:00","cost":50},
     "why":"Outdoor stop during rain window"}
  ],
  "created_at": "..."
}
```

### Expenses / Budget
| Method | Path | Notes |
|---|---|---|
| POST | `/trips/{id}/expenses` | `{category, amount, currency?, description?, spent_at?, item_stable_key?}` |
| GET | `/trips/{id}/expenses` | List |
| DELETE | `/expenses/{id}` | |
| GET | `/trips/{id}/budget` | `{planned_total, actual_total, remaining, by_category:[{category, planned, actual}], overrun_pct}` |

### Demo mode
| Method | Path | Notes |
|---|---|---|
| POST | `/demo/simulate` | `{trip_id, type: "weather"|"closure"|"delay"|"budget_overrun", day_index, params?}` -> starts `replan_graph` with injected signals. Returns `{run_id}` |

### Misc
| GET | `/places/search?city=&q=&category=` | Search the cached catalog (for manual add) |
| GET | `/health` | Liveness |

---

## 2. SSE Event Stream

`GET /agent/runs/{run_id}/stream` -> `text/event-stream`. Each event:

```
id: 14
event: step
data: {"seq":14,"type":"step","node":"researcher","message":"Found 12 candidate places","status":"done","payload":{}}

```

`id` = `agent_run_events.seq` (use as `Last-Event-ID` for reconnect; backend replays missed events from the DB).

| `type` | When | `payload` |
|---|---|---|
| `step` | Node started/finished | `{}` |
| `tool_call` | Tool invoked | `{"tool":"get_weather_forecast","args":{...}}` |
| `tool_result` | Tool returned | `{"tool":"...","ok":true,"summary":"80% rain Day 2 14-18h","cached":false}` |
| `llm_call` | Model call completed | `{"model":"gemini-...","latency_ms":2100}` (also model switch notices: `"fallback":true`) |
| `draft` | Partial itinerary available | `{"days_ready":[1,2]}` |
| `disruption` | Disruption detected | `DisruptionEvent` object |
| `proposal` | Proposal created, run is `awaiting_user` | `{"proposal_id":"..."}` |
| `token` | Streaming chat tokens (chat runs only) | `{"text":"..."}` |
| `error` | Recoverable/fatal error | `{"code":"llm_rate_limited","recoverable":true,"message":"..."}` |
| `done` | Run finished | `{"status":"completed","version_id":"...?","proposal_id":"...?"}` |

Frontend rules:
- Append `step`/`tool_*` to the timeline; update by `node` + `message` when `status` changes.
- On `done`, refetch `/trips/{id}/itinerary`.
- On `proposal`, show the banner and fetch `/proposals/{id}`.
- Send a keep-alive comment (`: ping`) every 15s from the server.

---

## 3. Agent <-> Backend Interface (Python)

```python
# app/agents/gateway.py
from typing import AsyncIterator

class AgentEvent(BaseModel):
    type: Literal["step","tool_call","tool_result","llm_call","draft",
                  "disruption","proposal","token","error","done"]
    node: str | None = None
    message: str | None = None
    status: Literal["running","done","failed"] | None = None
    payload: dict = {}

async def run_plan(run_id: UUID, trip_id: UUID, db: AsyncSession) -> AsyncIterator[AgentEvent]: ...
async def run_replan(run_id: UUID, trip_id: UUID, db: AsyncSession,
                     injected: InjectedSignals | None = None) -> AsyncIterator[AgentEvent]: ...
async def resume_replan(run_id: UUID, decision: Literal["approve","reject"], note: str | None) -> AsyncIterator[AgentEvent]: ...
async def run_chat(run_id: UUID, trip_id: UUID, message: str, db: AsyncSession) -> AsyncIterator[AgentEvent]: ...
```

Execution pattern in the router:
1. Create `agent_runs` row (status `queued`), return `run_id` (202).
2. A background task iterates the generator, writes each event to `agent_run_events` (assigning `seq`), and publishes to an in-memory/Redis pub-sub channel `run:{run_id}`.
3. The SSE endpoint replays stored events after `Last-Event-ID`, then tails the channel until `done`/`error`.
4. Graph config: `{"configurable": {"thread_id": str(run_id)}}`, using `AsyncPostgresSaver`.
5. Resume: `graph.astream(Command(resume={"decision": ...}), config)`.

### Core Pydantic models (shared)

```python
class TripSpec(BaseModel):
    trip_id: UUID; destination: str; start_date: date; end_date: date
    group_size: int; budget_total: Decimal; currency: str
    pace: Literal["relaxed","balanced","packed"]; vibe_tags: list[str]; notes: str | None

class DraftItem(BaseModel):
    stable_key: UUID | None = None
    day_index: int; position: int
    place_id: UUID | None; title: str
    category: str; setting: Literal["indoor","outdoor","mixed"]
    start_time: time; end_time: time; est_cost: Decimal
    lat: float | None; lng: float | None
    is_locked: bool = False
    travel_mode: str | None; travel_minutes: int | None

class ItineraryDraft(BaseModel):
    items: list[DraftItem]; summary: str

class Violation(BaseModel):
    code: Literal["closed","overlap","travel_too_long","over_budget","day_too_long","locked_changed"]
    item_stable_key: UUID | None; day_index: int | None; detail: str

class DisruptionEvent(BaseModel):
    type: str; severity: Literal["low","medium","high"]
    day_index: int | None; window_start: datetime | None; window_end: datetime | None
    affected_stable_keys: list[UUID]; summary: str; source: str; data: dict = {}

class InjectedSignals(BaseModel):          # demo mode
    type: Literal["weather","closure","delay","budget_overrun"]
    day_index: int; params: dict = {}      # e.g. {"precip_prob": 0.9, "from": "14:00", "to": "18:00"}
```

### Validator rules (deterministic, unit-tested)
1. No overlapping items in a day; start < end.
2. Item inside opening hours (skip if `hours_confidence = unknown`, but add flag).
3. `travel_minutes` between consecutive items fits in the gap.
4. Day active time <= pace limit (relaxed 8h, balanced 10h, packed 12h).
5. Total cost <= budget_total (and per-day cap if set).
6. Locked items unchanged in time and position.

### Impact analyzer rules (deterministic)
- **weather:** outdoor/mixed item overlapping hours with `precip_prob >= 0.6` -> affected.
- **closure/hours:** item time outside the refreshed opening hours or the place marked closed.
- **delay:** a travel leg's new estimate exceeds the planned one by >= 30 min -> downstream items affected.
- **budget_overrun:** actual > planned by >= 10% -> propose cost reductions on unlocked future items.

---

## 4. Error Format

```json
{"error": {"code": "validation_error", "message": "end_date must be after start_date", "details": [...]}}
```
Codes: `validation_error`, `unauthorized`, `forbidden`, `not_found`, `run_in_progress`, `llm_unavailable`, `tool_unavailable`, `rate_limited`, `internal_error`.

## 5. Handoff Checklist

- [ ] Backend: ship stub `/generate` + SSE with canned events first, so frontend can build against it.
- [ ] Backend: publish OpenAPI (`/docs`) and generate TS types for the frontend.
- [ ] Agents: validator + impact analyzer built as pure functions with tests before wiring the LLM.
- [ ] Agents: all LLM outputs use structured output with Pydantic models above.
- [ ] Frontend: render timeline from SSE `type`s; handle `Last-Event-ID` reconnect.
- [ ] Shared: seed data for 3-4 demo cities and 10 scripted disruption scenarios.
