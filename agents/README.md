# Reroute Agent Runtime

Autonomous, deterministic, and adaptive travel planning system built with LangChain, LangGraph, and Pydantic v2.

---

## 1. Overview

Reroute generates day-by-day itineraries, continuously monitors them against live real-world signals (weather, mountain pass closures, traffic delays, and budget burn), and proposes targeted, minimal replans.

### Core Architectural Principles
- **Deterministic Validation & Impact Analysis**: Pure mathematical functions govern validity. LLMs propose; deterministic code validates.
- **Human-in-the-Loop (HITL)**: No modification is ever applied without traveler approval. The replanner halts at `interrupt()` until approved or rejected.
- **Strict Invariance**: Replans modify only affected stops. Unaffected and locked items remain byte-identical.
- **Decoupled Persistence**: Agents code against Protocol interfaces (`TripRepository`, `ItineraryRepository`, `ProposalRepository`, `DisruptionRepository`, `PlaceCatalogRepository`, `ExpenseRepository`, `CacheRepository`, `RunEventRepository`).

---

## 2. Directory Structure

```
agents/
  pyproject.toml            # Project dependencies, ruff, mypy, and pytest config
  .env.example              # Environment variable template
  README.md                 # System overview and operational guide
  PLAN.md                   # Initial specification analysis and build plan
  INTEGRATION_NOTES.md      # Backend engineer handoff notes
  DECISIONS.md              # Architectural trade-offs log
  cli.py                    # Standalone CLI runner for local demo and simulation
  reroute_agents/           # Importable agent package
    api.py                  # FastAPI REST and SSE router/app
    config.py               # Environment configuration and thresholds
    gateway.py              # Public async generators yielding AgentEvents
    llm.py                  # Tiered fallback chains and FakeLLM
    state.py                # Pydantic contract models and LangGraph states
    events.py               # AgentEvent factories and SSE wire format
    monitor.py              # Background trip evaluation worker
    graphs/                 # LangGraph definitions
      plan_graph.py         # Plan generation with bounded 3-iteration fix loop
      replan_graph.py       # Disruption replanning with interrupt() HITL
      chat_graph.py         # Conversational concierge assistant
    nodes/                  # Graph node implementations
      intake.py researcher.py planner.py validator.py budget_check.py
      finalize.py collect_signals.py impact_analyzer.py replanner.py
      build_proposal.py apply_changes.py
    rules/                  # Pure deterministic rule engines
      validator_rules.py impact_rules.py altitude.py seasonal.py permits.py
    destinations/           # Destination registry and seed loader
      registry.py
    repositories/           # Storage abstraction layer
      interfaces.py         # Typing protocols
      in_memory.py          # High-performance in-memory implementations
    prompts/                # Versioned markdown prompt templates
      planner_v1.md replanner_v1.md chat_v1.md
    evaluation/             # Benchmarks
      scenarios.py          # 20 scripted trips and 10 disruptions
      run_eval.py           # Scoring runner
  data/                     # Regional catalogs
    seed/
      darjeeling.json north_sikkim.json arunachal.json ladakh.json routes.json
    README.md               # Audit log of verified vs unverified records
  evaluation/
    RESULTS.md              # Target evaluation benchmark metrics
  tests/
    unit/                   # Rules, tools, monitor, and security guardrail tests
    graph/                  # plan_graph, replan_graph, and chat_graph tests
    integration/            # Contract SSE event sequencing and invariant tests
    evaluation/             # Target benchmark regression tests
```

---

## 3. Setup and Installation

### Requirements
- Python 3.11+
- pip

### Install Dependencies
From the repository root:
```bash
pip install -e ./agents
```

### Environment Configuration
Copy the template to `.env`:
```bash
cp agents/.env.example agents/.env
```
Key configuration parameters:
- `LLM_STRONG_CHAIN`: Fallback provider chain (e.g. `gemini:gemini-2.5-flash,groq:llama-3.3-70b-versatile`).
- `LLM_SMALL_CHAIN`: Fallback provider chain for lightweight tasks.
- `GOOGLE_API_KEY`: API key for Google Gemini models.
- `GROQ_API_KEY`: API key for Groq models.
- `MOCK_TOOLS`: Set to `true` for offline execution.
- `MOCK_LLM`: Set to `true` to force FakeLLM fallback.

---

## 4. Running the Local CLI

`agents/cli.py` provides standalone execution using in-memory repositories and MemorySaver checkpointing.

### 4.1 Generate an Itinerary
```bash
# Offline with FakeLLM and curated seed catalog
python agents/cli.py plan --city darjeeling --days 3 --budget 15000 --pace balanced --tags food,nature --fake-llm

# Using live LLM (when GOOGLE_API_KEY or GROQ_API_KEY is set)
python agents/cli.py plan --city darjeeling --days 3 --budget 15000 --pace balanced
```

### 4.2 Simulate a Real-World Disruption (Demo HITL)
```bash
python agents/cli.py simulate --type weather --day 2 --fake-llm
```
This runs the replan graph, detects affected outdoor stops, produces a diff proposal, pauses via `interrupt()`, and prompts for traveler input on terminal:
`Decision Options: [approve / reject / alternatives]`
Entering `approve` updates the itinerary to Version 2.

### 4.3 Validate an Itinerary File
```bash
python agents/cli.py check-rules --file sample_itinerary.json
```

### 4.4 Run Standalone Agent API Server
```bash
python agents/cli.py serve --port 8000
# Or directly via uvicorn:
uvicorn reroute_agents.api:app --host 127.0.0.1 --port 8000
```

---

## 5. Running the Test Suite & Quality Gates

Run all quality checks and test suites:

```bash
# 1. Run full pytest suite (Unit, Graph, Invariant, Contract, and Benchmark tests)
pytest agents/tests/

# 2. Run Ruff linter and formatter checks
ruff check agents
ruff format --check agents

# 3. Run Mypy strict type checking
mypy agents/reroute_agents
```

### Run Benchmark Suite
```bash
python -m reroute_agents.evaluation.run_eval
```
Generates `agents/evaluation/RESULTS.md` asserting system performance against PRD Section 9 targets.

---

## 6. Backend Integration

The backend imports the async generators from `reroute_agents.gateway`:
```python
from reroute_agents.gateway import run_plan, run_replan, resume_replan, run_chat
from reroute_agents.state import TripSpec, InjectedSignals, AgentEvent

# Run plan generation and stream SSE
async for event in run_plan(run_id, trip_id, db=session):
    yield sse_format(event)

# Resume replan on user approval
async for event in resume_replan(run_id, decision="approve"):
    yield sse_format(event)
```
See `agents/INTEGRATION_NOTES.md` for complete details on repository adapters and checkpointer injection.
