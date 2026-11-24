# Reroute Agent Codebase Walkthrough: Architecture, Design, and Implementation

---

## 1. What the Agent Package Is (In Plain Words)

The Reroute agent package (`agents/reroute_agents/`) is an autonomous travel intelligence engine designed specifically for complex, high-risk travel itineraries (such as Himalayan mountain corridors in Ladakh, Spiti, Darjeeling, and Arunachal Pradesh).

### What Problem It Solves
Traditional travel planners generate static itineraries that fail the moment real-world events occur: a mountain pass closes due to a landslide, torrential rain strikes an outdoor hike, or flight delays cascade across multi-stop schedules. Standard consumer AI assistants often hallucinate travel feasibility, creating schedules that violate physical laws—such as scheduling two activities simultaneously, exceeding safe high-altitude ascent rates, or ignoring mandatory government permits.

Reroute solves this by separating **creative synthesis** from **deterministic validation**:
1. **The LLM is only a proposer**: It crafts day-by-day itineraries and proposes substitutions.
2. **Deterministic code is the decider**: Pure Python rule functions strictly enforce opening hours, drive times, altitude limits, and budget ceilings.
3. **The human traveler is the final authority**: No change to an active itinerary is ever applied without explicit traveler approval (`interrupt()` human-in-the-loop).

### What Goes In and What Comes Out
- **Inputs**: A structured trip specification (`TripSpec`) containing destination, dates, budget, group size, pace, and vibe tags; live environmental signals (weather forecasts, road closures, flight delays, expense receipts); conversational user queries.
- **Outputs**: Versioned, conflict-free itineraries (`ItineraryVersion` and `DraftItem`), structured proposal diffs (`ReplanProposal`), and a real-time asynchronous stream of typed server-sent events (`AgentEvent`).

### The Backend Boundary
The agent package is strictly decoupled from web harnesses, databases, and UI frontends. Its boundary ends at:
- **`gateway.py`**: The four asynchronous entry points (`run_plan`, `run_replan`, `resume_replan`, `run_chat`).
- **`repositories/interfaces.py`**: Abstract repository protocols for database persistence.
- **`checkpointer.py`**: State persistence interfaces for LangGraph.
- **`events.py`**: The SSE event payload format streamed to client applications.

The backend is treated as an external black box that calls the gateway and listens to the yielded event stream.

---

## 2. The Agentic Cycle Explained

In modern AI terminology, "agentic" does not mean giving an LLM free rein to modify databases. In Reroute, "agentic" means an autonomous, closed-loop feedback cycle: **Sense -> Analyze -> Propose -> Verify -> Human Decision -> Act -> Watch**.

```
[1. SENSE]        Collect live signals (weather, road closures, expenses)
      |
      v
[2. ANALYZE]      Deterministic rules map signals to affected stops (0 LLM calls)
      |
      v
[3. PROPOSE]      Autonomous LLM generates minimal, targeted substitutions
      |
      v
[4. VERIFY]       Pure deterministic rules audit feasibility (hours, gaps, altitude)
      |
      v
[5. DECIDE]       Human traveler reviews visual diff: Approve / Reject / Alternatives
      |
      v
[6. ACT]          Increment itinerary to v(N+1) only upon traveler approval
      |
      v
[7. WATCH]        Background monitor continuously senses next signals
```

### Autonomy vs. Human Oversight
- **Autonomous Subsystems**:
  - Sensing and deduplicating environmental disruptions.
  - Selecting candidate replacement venues matching the original category and vibe.
  - Computing driving intervals and validating opening hours.
  - Halting invalid plans before a traveler ever sees them.
- **Human Gated Boundary**:
  - Committing itinerary mutations. When a proposal is ready, LangGraph's `interrupt()` halts graph execution. The agent saves state to a persistent checkpoint and sleeps until the human acts.

### Why Rules Decide Validity, Not the LLM
LLMs are probabilistic pattern matchers; they cannot guarantee arithmetic correctness or consistent boundary enforcement. If you prompt an LLM "Is this 15,000 INR budget respected?", it will frequently answer "Yes" even when the itemized sum is 18,500 INR. In Reroute, rule evaluation is implemented as pure, unit-tested Python functions (`validate_itinerary()` and `analyze_disruptions()`). The LLM never decides whether an itinerary is valid.

---

## 3. Folder and File Map

The `agents/` directory is structured as follows (6,342 total lines of Python in `reroute_agents/` across 40 files):

```
agents/
  cli.py                               # 286 lines  : Command-line runner for plan, simulate, check-rules, serve
  pyproject.toml                       # Dependencies and configuration for ruff, mypy, pytest
  PLAN.md                              # Implementation blueprint and module-by-module plan
  DECISIONS.md                         # Architecture decision records (ADRs)
  INTEGRATION_NOTES.md                 # Contract handoffs and backend coordination notes
  STATUS_REPORT.md                     # System QA audit and stress test report
  FIX_LOG.md                           # Comprehensive defect fix log and regression evidence
  data/
    seed/
      arunachal.json                   # 15 places  : Tawang, Bomdila, Dirang catalog items
      darjeeling.json                  # 16 places  : Tiger Hill, tea estates, mall road catalog items
      ladakh.json                      # 16 places  : Leh, Pangong, Nubra, Khardung La catalog items
      north_sikkim.json                # 15 places  : Lachung, Yumthang, Lachen catalog items
      routes.json                      # 3 routes   : Seed transit segments with mountain multipliers
  reroute_agents/
    __init__.py                        # 3 lines    : Package marker exporting public symbols
    api.py                             # 607 lines  : FastAPI HTTP and SSE streaming router endpoints
    checkpointer.py                    # 49 lines   : LangGraph checkpointer factory (MemorySaver / Postgres)
    config.py                          # 92 lines   : Pydantic/dataclass environment configuration & thresholds
    events.py                          # 172 lines  : Factory helpers creating strongly-typed AgentEvents
    gateway.py                         # 333 lines  : Public gateway interface connecting routers to graphs
    llm.py                             # 257 lines  : Resilient LLM gateway, fallback chains, rate limiter
    monitor.py                         # 88 lines   : Autonomous background trip evaluation worker
    state.py                           # 208 lines  : Pydantic domain models and LangGraph state TypedDicts
    destinations/
      registry.py                      # 136 lines  : Seed catalog loader and destination bounding boxes
    evaluation/
      run_eval.py                      # 256 lines  : PRD benchmark evaluation harness (20 trips, 10 disruptions)
      scenarios.py                     # 488 lines  : Hard-coded evaluation scenarios across 4 regions
    graphs/
      chat_graph.py                    # 455 lines  : Conversational ReAct assistant with tool execution
      plan_graph.py                    # 95 lines   : Initial itinerary generation and validator loop
      replan_graph.py                  # 105 lines  : Disruption replanning, validator loop, HITL interrupt
    nodes/
      apply_changes.py                 # 112 lines  : Node applying traveler decision to itinerary version
      budget_check.py                  # 58 lines   : Node verifying total and daily budget caps
      build_proposal.py                # 173 lines  : Node generating diff and triggering interrupt()
      collect_signals.py               # 46 lines   : Node fetching live weather, road, and expense data
      finalize.py                      # 76 lines   : Node persisting final initial itinerary version v1
      impact_analyzer.py               # 70 lines   : Node mapping signals to affected itinerary stops
      intake.py                        # 23 lines   : Node validating trip specification inputs
      planner.py                       # 190 lines  : Node calling LLM to draft day-by-day itinerary
      replanner.py                     # 161 lines  : Node calling LLM to propose targeted substitutions
      researcher.py                    # 62 lines   : Node searching place catalog for matching vibes
      validator.py                     # 60 lines   : Node executing pure deterministic validator rules
    repositories/
      in_memory.py                     # 348 lines  : Complete in-memory repository implementation
      interfaces.py                    # 131 lines  : Abstract repository protocol interfaces
    rules/
      altitude.py                      # 132 lines  : Acclimatization and 1200m elevation jump rules
      impact_rules.py                  # 308 lines  : Signal disruption detection and SHA-256 fingerprinting
      permits.py                       # 69 lines   : Inner Line Permit (ILP) and PAP compliance rules
      seasonal.py                      # 81 lines   : Mountain pass seasonal closure rules (Rohtang, etc.)
      validator_rules.py               # 242 lines  : Core pure validation logic (overlaps, gaps, hours)
    tools/
      base.py                          # 74 lines   : Safe tool wrapper decorator with cache and timeouts
      currency.py                      # 106 lines  : Currency conversion tool with fixed offline fallback
      expenses.py                      # 38 lines   : Actual incurred expense tracking tool
      injector.py                      # 77 lines   : Test disruption signal injector
      places.py                        # 84 lines   : Catalog search and place details tool
      routing.py                       # 136 lines  : Distance, duration, and mountain multiplier routing tool
      weather.py                       # 141 lines  : Weather forecast and precipitation probability tool
```

---

## 4. Suggested Reading Order

To master the architecture in approximately two hours, read these 12 files in order:

1. **`agents/reroute_agents/state.py`**
   *What to look for*: The core data structures. Note `TripSpec`, `DraftItem`, `Violation`, `DisruptionEvent`, `ReplanProposal`, and the three LangGraph state definitions (`PlanState`, `ReplanState`, `ChatState`).
2. **`agents/reroute_agents/events.py`**
   *What to look for*: The 10 standard event factory functions (`step_event`, `proposal_event`, `done_event`, etc.) and how payloads are formatted.
3. **`agents/reroute_agents/gateway.py`**
   *What to look for*: The 4 public functions (`run_plan`, `run_replan`, `resume_replan`, `run_chat`), how `thread_id` is bound to `run_id`, and how LangGraph state updates are converted into yielded `AgentEvent` streams.
4. **`agents/reroute_agents/graphs/plan_graph.py`**
   *What to look for*: The linear flow from `intake` to `researcher` to `planner`, followed by the conditional routing loop around `validator` and `budget_check`.
5. **`agents/reroute_agents/graphs/replan_graph.py`**
   *What to look for*: The disruption detection branch (`route_after_impact`), the substitution loop, and how `build_proposal` transitions to `apply_changes`.
6. **`agents/reroute_agents/nodes/build_proposal.py`**
   *What to look for*: Line 94, where `interrupt()` pauses execution and hands control back to the traveler.
7. **`agents/reroute_agents/nodes/apply_changes.py`**
   *What to look for*: How user decisions (`approve`, `reject`, `alternatives`) are processed and how itinerary versions are updated.
8. **`agents/reroute_agents/rules/validator_rules.py`**
   *What to look for*: `validate_itinerary()` and the pure, deterministic checks that inspect overlaps, travel gaps, and operating hours.
9. **`agents/reroute_agents/rules/impact_rules.py`**
   *What to look for*: `analyze_disruptions()` and `compute_disruption_fingerprint()`. Notice how signals map to item IDs without LLM intervention.
10. **`agents/reroute_agents/rules/altitude.py` and `seasonal.py`**
    *What to look for*: Domain-specific Himalayan constraints—the 1,200m ascent ceiling and high pass closures.
11. **`agents/reroute_agents/llm.py`**
    *What to look for*: `TokenBucketRateLimiter`, `ResilientLLMChain`, exponential backoff retry, and 1-shot repair prompts.
12. **`agents/reroute_agents/tools/base.py`**
    *What to look for*: The `@safe_tool` decorator, cache repository lookup, mock fallback, and exception normalization.

---

## 5. Deep Dive by Layer

### Layer 1: Gateway (`gateway.py`)
The gateway is the public API contract for the agent package. It exposes four asynchronous generators:
- `run_plan(run_id, trip_id, ...)`: Builds and executes `plan_graph`.
- `run_replan(run_id, trip_id, injected=..., ...)`: Collects signals and executes `replan_graph` up to the human interrupt.
- `resume_replan(run_id, decision=..., note=..., ...)`: Resumes the paused `replan_graph` from checkpoint using `Command(resume=...)`.
- `run_chat(run_id, trip_id, message=..., ...)`: Executes the conversational assistant `chat_graph`.

```python
# agents/reroute_agents/gateway.py:L257-L265
config = {"configurable": {"thread_id": str(run_id)}}
resume_cmd: Any = Command(resume={"decision": decision, "note": note})
async for chunk in graph.astream(resume_cmd, config=config, stream_mode="updates"):
    for _node_name, update in chunk.items():
        if isinstance(update, dict) and "events" in update:
            for evt in update["events"]: ...
```

**Key Invariant**: `thread_id` is always set to `str(run_id)`. This guarantees that state saved during an `interrupt()` in `run_replan` can be retrieved by `resume_replan` without session collisions.

### Layer 2: Graphs (`graphs/`)
The graphs coordinate multi-step workflows using LangGraph `StateGraph`:
- **Plan Graph (`plan_graph.py`)**:
  - `START -> intake -> researcher -> planner -> validator -> (loop back to planner if violations and iter < 3) -> budget_check -> finalize -> END`.
- **Replan Graph (`replan_graph.py`)**:
  - `START -> collect_signals -> impact_analyzer -> (END if no disruptions) -> replanner -> validator -> (loop if violations and iter < 2) -> build_proposal [interrupt] -> apply_changes -> END`.
- **Chat Graph (`chat_graph.py`)**:
  - `START -> chat_agent -> (tools -> chat_agent loop, capped at 5) -> finalize -> END`.

### Layer 3: Nodes (`nodes/`)
Every node is a standalone callable taking a `State` dict and returning an update dict:
- `intake_node` (`nodes/intake.py`): Validates that `trip_id` exists and emits `step_event`. Pure code.
- `researcher_node` (`nodes/researcher.py`): Calls `search_places` tool to retrieve destination candidates matching vibe tags.
- `planner_node` (`nodes/planner.py`): Assembles system prompt with places, dates, and budget; calls LLM using structured output (`ItineraryDraft`).
- `validator_node` (`nodes/validator.py`): Pure code. Calls `validate_itinerary(draft_items, spec)` and populates `state["violations"]`.
- `budget_check_node` (`nodes/budget_check.py`): Evaluates total and daily budget ceilings. Pure code.
- `finalize_node` (`nodes/finalize.py`): Persists version 1 to repository and emits `done_event`.
- `collect_signals_node` (`nodes/collect_signals.py`): Checks live weather, road notices, and incurred expenses.
- `impact_analyzer_node` (`nodes/impact_analyzer.py`): Pure code. Identifies which items are disrupted and computes SHA-256 fingerprints.
- `replanner_node` (`nodes/replanner.py`): Assembles replacement prompt. Keeps locked and unaffected items byte-identical.
- `build_proposal_node` (`nodes/build_proposal.py`): Generates structured diff, saves proposal, and executes `interrupt()`.
- `apply_changes_node` (`nodes/apply_changes.py`): Handles traveler response: updates version on approve, preserves existing on reject.

### Layer 4: Rules (`rules/`)
The rule engine contains pure functions with zero network dependencies:
- **`validator_rules.py`**:
  - `overlap`: Flags items whose time spans intersect on the same day.
  - `travel_gap`: Enforces a 30-minute buffer between different locations.
  - `opening_hours`: Compares start/end times against catalog `opening_hours`.
  - `budget_total` / `budget_daily_cap`: Validates total cost <= budget and daily cost <= daily ceiling.
  - `locked_item_modified`: Ensures items marked `locked=True` never change.
  - `pace_exceeded`: Maximum activities per day (relaxed: 3, balanced: 5, packed: 7).
- **`altitude.py`**: Enforces acclimatization rest days when ascending above 3,000m and prevents single-day elevation gains exceeding 1,200m.
- **`seasonal.py`**: Flags mountain passes (e.g. Rohtang Pass, Kunzum Pass) that close during winter months (November to May).
- **`permits.py`**: Flags destinations requiring government Inner Line Permits (ILP) or Protected Area Permits (PAP) (e.g., Pangong Tso, Tawang).
- **`impact_rules.py`**:
  - `weather_rain`: Precipitation probability >= 70% during outdoor activities.
  - `weather_snow`: Snowfall >= 5cm or visibility < 500m.
  - `closure`: Explicit venue or transit corridor closure.
  - `transit_delay`: Schedule delays >= 30 minutes cascading to later stops.
  - `budget_overrun`: Cumulative actual expenses >= 15% above estimate.

### Layer 5: Tools (`tools/`)
Tools interface with real-world or simulated data. All tools are wrapped with `@safe_tool` (`tools/base.py`), which guarantees:
1. Deterministic output when `settings.mock_tools` is `True`.
2. 3600-second caching in `api_cache`.
3. Artificial signal injection via `DisruptionInjector` (`tools/injector.py`).
4. 10-second timeout with 3-attempt tenacity retry.
5. Error normalization: returns `{"ok": False, "error": str(e)}` instead of raising exceptions.

Available tools:
- `WeatherTool` (`tools/weather.py`): Open-Meteo API integration with offline fallback.
- `RoutingTool` (`tools/routing.py`): OSRM / OpenRouteService routing with regional mountain road multipliers (1.4x - 1.8x).
- `PlacesTool` (`tools/places.py`): Destination place catalog search and lookup.
- `CurrencyTool` (`tools/currency.py`): Exchange rate conversions with fixed fallback rates.
- `ExpensesTool` (`tools/expenses.py`): Incurred expense ledger lookup.

### Layer 6: LLM Gateway (`llm.py`)
The LLM gateway abstracts model providers through `ResilientLLMChain`:
- **Model Tiers**:
  - `strong`: Gemini 2.5 Flash / Pro -> Groq Llama 3.3 70B Versatile.
  - `small`: Groq Llama 3.1 8B Instant -> Gemini 2.5 Flash.
  - `local`: Ollama Qwen 2.5 7B -> Ollama Llama 3.2 3B.
- **Token Bucket Rate Limiter**: Limits requests to 2.0 RPS with a burst capacity of 10 (`TokenBucketRateLimiter`).
- **Resilience**:
  - Retries up to 2 times with exponential backoff (`initial_delay = 1.0s, backoff_factor = 1.5`).
  - Catches rate limits and 5xx errors and switches to the next provider in the chain.
  - Implements 1-shot repair: if structured JSON parsing fails, `_invoke_with_repair` feeds the raw output and schema back to the model for automatic correction.

```python
# agents/reroute_agents/llm.py:L151-L157
repair_prompt = (
    f"The following output failed schema validation for {schema.__name__}:\n\n"
    f"{raw_text}\n\n"
    f"Validation error:\n{err}\n\n"
    f"Return ONLY valid JSON conforming to the schema."
)
```

### Layer 7: State and Events (`state.py`, `events.py`)
All communication with callers occurs via `AgentEvent` objects (`events.py`):
- `token`: Incremental LLM token streaming.
- `step`: High-level workflow progress (e.g., "Evaluating substitutions for 1 stop(s)").
- `draft`: Intermediate itinerary schedule proposed by planner.
- `proposal`: Replan proposal ready for traveler review (includes visual diff).
- `disruption`: Real-world environmental event detected by impact analyzer.
- `tool_call` / `tool_result`: Diagnostics of external tool invocations.
- `llm_call`: Metadata on model tier, provider, tokens, latency, and fallback flags.
- `done`: Successful termination signal.
- `error`: Error payload detailing failure reason and whether it is recoverable.

### Layer 8: Repositories (`repositories/`)
Data persistence is decoupled via Python protocols in `repositories/interfaces.py`:
- `TripRepository`: Trip specifications (`trips` table).
- `ItineraryRepository`: Itinerary versions and draft items (`itinerary_versions`, `itinerary_items`).
- `DisruptionRepository`: Active disruptions (`disruption_events`).
- `ProposalRepository`: Pending replan proposals (`replan_proposals`).
- `ExpenseRepository`: Recorded expenses.
- `PlaceCatalogRepository`: Destination places catalog.
- `CacheRepository`: Tool API response cache (`api_cache`).
- `RunEventRepository`: Complete audit trail of `AgentEvent` records (`agent_runs`, `agent_run_events`).

The package includes `InMemoryRepositories` (`repositories/in_memory.py`), which implements these protocols using thread-safe in-memory collections for fast, zero-dependency testing and CLI usage.

### Layer 9: Destinations and Seed Data (`destinations/`, `data/seed/`)
Seed catalogs provide verified geographic data across four Himalayan regions:
- `darjeeling.json` (16 places)
- `ladakh.json` (16 places)
- `north_sikkim.json` (15 places)
- `arunachal.json` (15 places)
- `routes.json` (3 inter-city transit corridors with mountain terrain multipliers)

Each place contains coordinates, altitude, opening hours, indoor/outdoor classification, category, estimated duration, cost, permit requirements, and seasonal accessibility tags.

### Layer 10: Monitor, CLI, Evaluation, and Tests
- **`monitor.py`**: Background sentry calling `evaluate_trip(trip_id, repos)`. Runs deterministically without calling LLMs.
- **`cli.py`**: Terminal utility supporting `plan`, `simulate`, `check-rules`, and `serve` (FastAPI server).
- **`evaluation/run_eval.py`**: Evaluates system against PRD Section 9 success metrics across 20 scripted trips and 10 disruptions.
- **Tests (`tests/`)**: Complete test suite of 126 unit, integration, and stress tests passing with 91% coverage.

---

## 6. Worked Example: Traced End to End

To understand the system in execution, we trace the real captured trace `02_replan_approve_run.json` (Simulated Day 2 Rain Disruption in Darjeeling).

### Initial Baseline (Version 1)
A 3-day balanced trip to Darjeeling with an outdoor afternoon visit to **Rock Garden** scheduled from 13:00 to 16:00 on Day 2.

### Step 1: Signal Collection
- **Node**: `collect_signals_node` (`nodes/collect_signals.py`)
- **Action**: Queries live weather forecast for Darjeeling and incurred expenses.
- **Signal**: Rainfall probability is 90% between 13:00 and 17:00 on Day 2.
- **Events Emitted**:
  1. `step [collect_signals]`: "Checking live weather, mountain road conditions, and expense totals"
  2. `step [collect_signals]`: "Signals collected successfully"

### Step 2: Impact Analysis and Fingerprinting
- **Node**: `impact_analyzer_node` (`nodes/impact_analyzer.py`)
- **Action**: Evaluates `analyze_disruptions()`. Rock Garden is an outdoor activity scheduled during the 13:00-17:00 rain window (`is_outdoor=True`).
- **Disruption Generated**:
  - Category: `weather_rain`, Severity: `medium`.
  - Affected Stop: Rock Garden (Day 2).
  - SHA-256 Fingerprint: Deterministic hash computed from `trip_id`, `category`, and `item_id`.
- **Events Emitted**:
  3. `disruption [impact_analyzer]`: "Precipitation likely on Day 2 (90%, 13:00-17:00)"
  4. `step [impact_analyzer]`: "Detected 1 disruption(s) affecting 1 stop(s)"

### Step 3: Targeted Autonomous Replanning
- **Node**: `replanner_node` (`nodes/replanner.py`)
- **Action**: The replanner queries the destination catalog for an indoor substitution matching the vibe. It selects the **Himalayan Mountaineering Institute (HMI) Museum** (indoor, open 09:00-17:00, cost 150 INR).
- **Constraint Check**: Morning and evening stops on Day 2 (Tiger Hill, Chowrasta) and all stops on Day 1 and Day 3 remain **byte-identical**.
- **Events Emitted**:
  5. `step [replanner]`: "Evaluating substitutions for 1 affected stop(s)"
  6. `step [replanner]`: "Prepared substitution proposal modifying 1 stop(s)"

### Step 4: Deterministic Validation
- **Node**: `validator_node` (`nodes/validator.py`)
- **Action**: `validate_itinerary()` evaluates the updated schedule. The museum fits opening hours, maintains the 30-minute travel gap, and complies with daily budget. Zero violations found.
- **Events Emitted**:
  7. `step [validator]`: "All constraint checks passed (hours, gaps, pace, altitude, and seasonal access)"

### Step 5: Proposal Generation and Human-in-the-Loop Interruption
- **Node**: `build_proposal_node` (`nodes/build_proposal.py`)
- **Action**: Computes diff: `[UPDATE] Day 2 | Rock Garden --> HMI Museum | Reason: Rain shelter substitution`. Cost delta: -50 INR.
- **Interruption**: Calls `interrupt({"proposal_id": prop.id})`. The graph pauses; state is frozen into checkpointer storage.
- **Events Emitted**:
  8. `proposal [build_proposal]`: "Replan proposal ready for review" (includes full diff payload)
  9. `step [build_proposal]`: "Proposal created (1 changes). Awaiting traveler decision."

### Step 6: Traveler Decision and Version Landed
- **Action**: The traveler clicks **Approve** in the UI. The backend calls `resume_replan(run_id, decision="approve")`.
- **Node**: `apply_changes_node` (`nodes/apply_changes.py`)
- **Execution**: The checkpointer reloads state. `apply_changes_node` increments the itinerary version to `v2` and marks the proposal approved.
- **Events Emitted**:
  10. `step [build_proposal]`: "Proposal resumed with traveler decision: approve"
  11. `step [apply_changes]`: "Changes approved. Itinerary successfully updated to v2."
  12. `done [apply_changes]`: "Execution finished with status: completed"

### Alternative Outcomes:
- **Reject Trace (`03_replan_reject_run.json`)**: If the traveler clicks **Reject**, `apply_changes_node` discards the proposal and emits "Proposal rejected. Existing itinerary preserved unchanged." Trip remains at version 1.
- **Alternatives Trace (`04_replan_alternatives_run.json`)**: If the traveler clicks **Alternatives**, `apply_changes_node` increments the iteration counter and loops back to `replanner_node` to propose a different indoor substitution (e.g., Darjeeling Himalayan Railway Museum).

---

## 7. Configuration and Environment

All runtime configuration is managed via `Settings` in `agents/reroute_agents/config.py`:

| Environment Variable | Default Value | Purpose | Behavior When Missing |
|---|---|---|---|
| `LLM_STRONG_CHAIN` | `gemini:gemini-2.5-flash,groq:llama-3.3-70b-versatile` | Primary model fallback chain for planning | Uses defaults; falls back to FakeLLM if keys missing |
| `LLM_SMALL_CHAIN` | `groq:llama-3.1-8b-instant,gemini:gemini-2.5-flash` | Lightweight chain for chat/summaries | Uses default fallback pair |
| `LLM_LOCAL_CHAIN` | `ollama:qwen2.5:7b,ollama:llama3.2:3b` | Offline local model chain | Skipped if Ollama server is unreachable |
| `GOOGLE_API_KEY` | `None` | API key for Gemini models | Skips Gemini provider in fallback chain |
| `GROQ_API_KEY` | `None` | API key for Groq models | Skips Groq provider in fallback chain |
| `MOCK_TOOLS` | `false` | Deterministic tool execution flag | If true, tools return canned seed data without network |
| `MOCK_LLM` | `false` | Deterministic FakeLLM flag | If true, gateway uses FakeLLM for zero-cost runs |
| `LLM_RATE_LIMIT_RPS` | `2.0` | Maximum LLM requests per second | Token bucket throttles calls exceeding 2.0 RPS |
| `LLM_TOKEN_BURST` | `10` | Maximum token bucket burst capacity | Allows bursts up to 10 calls before strict rate throttling |
| `ALTITUDE_ACCLIMATIZATION_THRESHOLD_M` | `1000` | Minimum elevation gain requiring acclimatization | Defaults to 1,000 meters |
| `ALTITUDE_HIGH_RISK_THRESHOLD_M` | `3000` | Baseline elevation triggering high-altitude rules | Defaults to 3,000 meters (e.g. Leh, Spiti) |
| `MAX_DRIVE_HOURS_PER_DAY` | `7` | Maximum safe driving duration per day | Rejects driving routes exceeding 7 hours in mountains |
| `ALLOW_NIGHT_DRIVING` | `false` | Flag permitting travel after 20:00 | Flags travel after 20:00 on mountain passes as unsafe |

---

## 8. Safety and Reliability Mechanisms

Reroute implements multi-layered defensive engineering to prevent failure modes:

1. **Human Approval Invariant**: No itinerary change is ever written to storage without explicit approval. Enforced by `interrupt()` in `nodes/build_proposal.py:L94`. Tested in `tests/graph/test_replan_graph.py`.
2. **Locked Item Immutability**: Stops marked `locked=True` (e.g., pre-paid flights or hotel bookings) are strictly preserved byte-for-byte during replanning. Tested in `tests/integration/test_invariants.py`.
3. **Bounded Graph Iteration Loops**:
   - `max_plan_iterations = 3`: Planner fix loop terminates at 3 iterations, flagging unresolved issues rather than hanging.
   - `max_replan_iterations = 2`: Replanner substitution loop caps at 2 attempts.
   - `max_chat_iterations = 5`: Chat tool loop caps at 5 turns.
4. **Resilient LLM Failover**: Provider-level fallback (Gemini -> Groq -> Ollama) with exponential backoff and 1-shot schema repair. Tested in `tests/stress/test_llm_stress.py`.
5. **Token Bucket Rate Limiting**: In-memory token bucket prevents 429 quota exhaustion under concurrency. Tested with 30 simultaneous trips in `tests/stress/test_llm_stress.py`.
6. **Tool Error Normalization**: `@safe_tool` decorator catches network exceptions, 5xx responses, and timeouts, normalizing them into `{"ok": False, "error": msg}` so agent graphs never crash on upstream tool failure.
7. **Disruption Deduplication**: SHA-256 fingerprinting prevents infinite replan storms when the monitor senses recurring weather conditions.

---

## 9. Differences from the Spec

The codebase adheres strictly to the architectural contracts in `docs/03_ARCHITECTURE.md` and `docs/05_API_AND_AGENT_CONTRACT.md`. The table below documents intentional design adaptations implemented in the code:

| Item | Spec Source | Code Implementation | Rationale | Impact |
|---|---|---|---|---|
| **Intake Classification** | `03_ARCHITECTURE.md` Sec 2.1 | `nodes/intake.py` validates `TripSpec` deterministically without an LLM | Trip specifications submitted from UI forms are already structured; an LLM classifier adds latency and failure points | Zero token cost for intake; faster startup (saves ~1.2s per run) |
| **Checkpointer Default** | `03_ARCHITECTURE.md` Sec 3.2 | Defaults to `MemorySaver` in-memory checkpointer; accepts `PostgresSaver` if connection string provided | Allows the agent package, test suite, and CLI to run completely offline without an active Postgres container | Zero infrastructure setup required for local development and evaluation |
| **Chat Architecture** | `03_ARCHITECTURE.md` Sec 2.3 | Single ReAct agent (`chat_agent_node`) with safe tools rather than multiple sub-agents | A single ReAct agent with strict tool boundaries avoids multi-agent orchestration overhead while achieving identical capabilities | Lower latency; simpler debugging; identical user-facing behavior |
| **Replan Iteration Cap** | `05_API_AND_AGENT_CONTRACT.md` Sec 4 | `max_replan_iterations` set to 2 (instead of 3) | Re-evaluating alternatives more than twice in an automated flow indicates unresolvable destination constraints | Prevents excessive user waiting; cleanly exits if 2 rounds fail |

---

## 10. Known Issues and Operational Limits

Based on thorough codebase verification and test execution:

1. **Evaluation Uses FakeLLM by Default**: The automated test suite (`pytest`) runs with `FakeLLM` and `MOCK_TOOLS=true` to guarantee deterministic, zero-cost, offline execution in CI/CD. While this proves that graph routing, state reducers, pure rules, and event streaming work with 100% precision, it does not evaluate live Gemini/Groq prompt quality or non-deterministic hallucinations. Live model evaluation requires setting real API keys and running `evaluation/run_eval.py --live`.
2. **In-Memory Default Repositories**: When running standalone CLI commands or unit tests without an active database, data is stored in volatile memory (`InMemoryRepositories`). If the process restarts, prior trip checkpoints are reset. Production deployments must inject persistent repository adapters connected to Postgres.
3. **Seed Data Scope**: The offline catalog currently includes 62 verified places across 4 Himalayan regions (Ladakh, Spiti, Darjeeling, Arunachal). It is not a global worldwide database; queries for unseeded cities will return empty candidate lists unless custom places are ingested.

---

## 11. How to Extend the System

### 1. How to Add a New City / Destination
1. Create `agents/data/seed/<city_name>.json` following the place catalog schema (see `darjeeling.json`).
2. Add bounding box and catalog mapping in `agents/reroute_agents/destinations/registry.py`:
   ```python
   # agents/reroute_agents/destinations/registry.py:L25
   DESTINATION_BOUNDS["manali"] = BoundingBox(lat_min=32.2, lat_max=32.3, lon_min=77.1, lon_max=77.2)
   ```
3. Load the file in `load_seed_catalog_into_repository()`.

### 2. How to Add a New Validator Rule
1. Define the rule check in `agents/reroute_agents/rules/validator_rules.py`.
2. Add a unique `ViolationCode` in `agents/reroute_agents/state.py` (e.g., `"museum_pass_missing"`).
3. Append the rule call to `validate_itinerary()`:
   ```python
   # agents/reroute_agents/rules/validator_rules.py
   v = check_custom_rule(items, spec)
   if v: violations.extend(v)
   ```
4. Add a unit test in `agents/tests/unit/test_rules.py`.

### 3. How to Add a New Disruption Type
1. Add the disruption code to `DisruptionCategory` in `agents/reroute_agents/state.py` (e.g., `"wildfire"`).
2. Implement signal matching logic in `agents/reroute_agents/rules/impact_rules.py`:
   ```python
   # agents/reroute_agents/rules/impact_rules.py
   if signal.get("wildfire_air_quality_index", 0) > 300:
       # create DisruptionEvent and flag outdoor stops
   ```
3. Update `compute_disruption_fingerprint()` to include the new signal attributes.

### 4. How to Add a New Tool
1. Define the tool function in `agents/reroute_agents/tools/<new_tool>.py`.
2. Decorate the function with `@safe_tool("new_tool_cache_key")`.
3. Provide a deterministic mock fallback block inside the function when `settings.mock_tools` is True.
4. Import and bind the tool in `agents/reroute_agents/graphs/chat_graph.py` or calling nodes.

### 5. How to Add a New Model Provider
1. Open `agents/reroute_agents/llm.py`.
2. In `ResilientLLMChain._create_model()`, add provider parsing (e.g. `anthropic:claude-3-5-sonnet`):
   ```python
   elif provider == "anthropic":
       from langchain_anthropic import ChatAnthropic
       return ChatAnthropic(model=model_name, api_key=...)
   ```
3. Add the model string to `LLM_STRONG_CHAIN` in `agents/reroute_agents/config.py`.

---

## 12. Technical Glossary

- **Agentic Loop**: A closed-loop control system where an autonomous agent senses external state, plans an action, verifies constraints, and executes mutations.
- **StateGraph**: The core LangGraph compilation class that coordinates nodes, channels, and conditional edges as a directed acyclic or cyclic graph.
- **Node**: A discrete Python function within a state graph that receives current state, performs execution, and returns a state update dictionary.
- **Edge**: A deterministic directed link between two nodes in a graph.
- **Conditional Edge**: A dynamic routing function that inspects current graph state and returns the string name of the next node to execute.
- **Checkpointer**: A persistence mechanism (`MemorySaver` or `PostgresSaver`) that serializes graph state at every super-step, enabling pause, resume, and time-travel debugging.
- **Interrupt (`interrupt()`)**: A LangGraph primitive that immediately halts graph execution and yields control back to the caller while saving state to storage.
- **Thread ID (`thread_id`)**: A unique partition key in the checkpointer. In Reroute, `thread_id` is set to `str(run_id)`.
- **Structured Output**: Forcing an LLM to return JSON adhering strictly to a Pydantic schema using constrained decoding or function calling.
- **Fallback Chain**: An ordered sequence of model providers (e.g. Gemini -> Groq -> Ollama) attempted sequentially when errors or rate limits occur.
- **Token Bucket**: A rate-limiting algorithm that maintains a bucket of tokens refilled at a constant rate, accommodating transient bursts while capping long-term request rates.
- **Disruption Fingerprint**: A deterministic SHA-256 hash computed from trip ID, disruption category, date, and impacted stop ID, used to deduplicate recurring alerts.
- **Server-Sent Events (SSE)**: A unidirectional HTTP protocol allowing the server to stream real-time JSON events (`AgentEvent`) to the client over a persistent connection.
- **Pure Function**: A function that has no side effects and always returns the same output given the same inputs (e.g. Reroute's validator and impact rules).
