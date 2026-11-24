# Reroute Agent Architecture Consolidation and Inventory

## 1. Executive Summary

This document details the code inventory, identifies redundant/dead patterns, and establishes the consolidation plan to reorganize the Reroute agent codebase into exactly four dedicated agents:
1. **Web Agent** (`agents/reroute_agents/agents/web/`): Web search, page fetching, geocoding, and place extraction into fixed `ResearchResult` schemas.
2. **Plan Agent** (`agents/reroute_agents/agents/plan/`): Day-by-day itinerary construction from researched places and catalog seeds.
3. **Replan Agent** (`agents/reroute_agents/agents/replan/`): Disruption detection, impact analysis, and alternative proposal generation.
4. **Chat Agent** (`agents/reroute_agents/agents/chat/`): Conversational ReAct assistant for traveler questions and user-requested itinerary modifications.

---

## 2. Codebase Inventory

| Module | Lines | Current Role | Target Destination & Action |
| :--- | :--- | :--- | :--- |
| `reroute_agents/__init__.py` | 3 | Package export marker | Retain package root |
| `reroute_agents/state.py` | 208 | Pydantic models, TripSpec, DraftItem, ReplanProposal | Preserved contract; models shared across agents |
| `reroute_agents/events.py` | 172 | AgentEvent and event builders (step, tool_call, etc.) | Preserved contract; shared across agents |
| `reroute_agents/config.py` | 92 | Environment settings (Pydantic BaseSettings) | Preserved; add web search & timeout configs |
| `reroute_agents/checkpointer.py` | 49 | LangGraph checkpointer initialization | Shared persistence utility |
| `reroute_agents/llm.py` | 257 | ResilientLLMChain, FakeLLM, TokenBucket | Shared LLM gateway across agents |
| `reroute_agents/gateway.py` | 333 | Public API entrypoints (`run_plan`, `run_replan`, etc.) | Public contract preserved; calls agent graphs |
| `reroute_agents/api.py` | 607 | FastAPI router for REST/SSE endpoints | Preserved boundary adapter |
| `reroute_agents/monitor.py` | 88 | Active trip disruption monitor background loop | Replan support service |
| `reroute_agents/destinations/registry.py` | 136 | Seed catalog loader & destination normalizer | Shared data utility |
| `reroute_agents/repositories/interfaces.py` | 131 | Protocol definitions for repository adapters | Shared repository contracts |
| `reroute_agents/repositories/in_memory.py` | 348 | In-memory mock repositories for testing/offline | Preserved for test execution |
| `reroute_agents/rules/validator_rules.py` | 242 | Pure function schedule & constraint validator | Shared deterministic rules engine |
| `reroute_agents/rules/impact_rules.py` | 308 | Pure function disruption impact analyzer | Replan agent core rules |
| `reroute_agents/rules/altitude.py` | 132 | High-altitude ascent & acclimatization rules | Validator rules helper |
| `reroute_agents/rules/permits.py` | 69 | Regional ILP & PAP permit deadline rules | Validator rules helper |
| `reroute_agents/rules/seasonal.py` | 81 | Winter pass closure & seasonal accessibility | Validator rules helper |
| `reroute_agents/tools/base.py` | 74 | `BaseTool`, `ToolResult`, caching decorator | Preserved base tool abstractions |
| `reroute_agents/tools/registry.py` | NEW | Agent-scoped tool registry (`for_agent(name)`) | Enforces dedicated agent tool access |
| `reroute_agents/tools/currency.py` | 106 | Currency conversion tool | Dedicated to **Chat Agent** |
| `reroute_agents/tools/expenses.py` | 38 | Expense query and logging tool | Dedicated to **Chat Agent** |
| `reroute_agents/tools/places.py` | 84 | Place catalog lookup tool | Dedicated to **Chat Agent** & **Plan Agent** |
| `reroute_agents/tools/routing.py` | 136 | Travel time and distance tool (ORS/haversine) | Dedicated to **Plan Agent** & **Chat Agent** |
| `reroute_agents/tools/weather.py` | 141 | Weather forecast query tool | Dedicated to **Replan Agent** |
| `reroute_agents/tools/injector.py` | 77 | Disruption signal injector tool | Dedicated to **Replan Agent** |
| `reroute_agents/tools/search.py` | NEW | Web search provider (Tavily, DDG, Mock) | Dedicated to **Web Agent** |
| `reroute_agents/tools/fetch.py` | NEW | Web page fetcher with SSRF guard and text parse | Dedicated to **Web Agent** |
| `reroute_agents/tools/geocode.py` | NEW | Geocoding service with rate limiter & bbox filter | Dedicated to **Web Agent** |
| `reroute_agents/nodes/intake.py` | 23 | Graph node: Unpack TripSpec into state | Merge into `agents/plan/nodes.py` |
| `reroute_agents/nodes/researcher.py` | 62 | Graph node: Seed catalog searcher (flawed) | Replaced by Web Agent delegation in Plan Agent |
| `reroute_agents/nodes/planner.py` | 190 | Graph node: LLM / deterministic schedule builder | Merge into `agents/plan/nodes.py` |
| `reroute_agents/nodes/validator.py` | 60 | Graph node: Wraps pure validator rules | Shared node / Plan & Replan |
| `reroute_agents/nodes/budget_check.py` | 58 | Graph node: Budget cap validator | Merge into `agents/plan/nodes.py` |
| `reroute_agents/nodes/finalize.py` | 76 | Graph node: Persist itinerary version 1 | Merge into `agents/plan/nodes.py` |
| `reroute_agents/nodes/collect_signals.py` | 46 | Graph node: Ingest active disruptions | Merge into `agents/replan/nodes.py` |
| `reroute_agents/nodes/impact_analyzer.py` | 70 | Graph node: Disruption impact analysis | Merge into `agents/replan/nodes.py` |
| `reroute_agents/nodes/replanner.py` | 161 | Graph node: Repair itinerary schedule | Merge into `agents/replan/nodes.py` |
| `reroute_agents/nodes/build_proposal.py` | 173 | Graph node: Diff calculation & interrupt() | Merge into `agents/replan/nodes.py` |
| `reroute_agents/nodes/apply_changes.py` | 112 | Graph node: Commit approved proposal to DB | Merge into `agents/replan/nodes.py` |
| `reroute_agents/graphs/plan_graph.py` | 95 | Plan StateGraph definition | Wire to `agents/plan/agent.py` |
| `reroute_agents/graphs/replan_graph.py` | 105 | Replan StateGraph definition | Wire to `agents/replan/agent.py` |
| `reroute_agents/graphs/chat_graph.py` | 455 | Chat ReAct StateGraph definition | Wire to `agents/chat/agent.py` |

---

## 3. Dedicated Agent Structure and Boundaries

To eliminate overlapping scripts and ensure clear architectural boundaries, the four agents are organized under `agents/reroute_agents/agents/`:

```
agents/reroute_agents/
  ├── agents/
  │   ├── web/
  │   │   ├── __init__.py
  │   │   ├── schemas.py          # ResearchResult, PlaceResearchItem
  │   │   ├── agent.py            # Web research graph / workflow
  │   │   └── tools.py            # Bound instances of search, fetch, geocode
  │   ├── plan/
  │   │   ├── __init__.py
  │   │   ├── agent.py            # Plan graph entrypoint & state definition
  │   │   └── nodes.py            # Intake, draft generation, validation, finalize
  │   ├── replan/
  │   │   ├── __init__.py
  │   │   ├── agent.py            # Replan graph entrypoint & state definition
  │   │   └── nodes.py            # Signal collection, impact, repair, proposal, apply
  │   └── chat/
  │       ├── __init__.py
  │       ├── agent.py            # Chat ReAct assistant & proposal builder
  │       └── tools.py            # Bound chat tools (places, routing, expenses, currency)
  ├── tools/
  │   ├── registry.py             # Agent tool access registry with for_agent()
  │   ├── search.py               # Web search (Tavily/DDG/Mock)
  │   ├── fetch.py                # Page fetcher with SSRF guard
  │   ├── geocode.py              # Geocoding with Nominatim & bounding box
  │   ├── places.py               # Catalog place queries
  │   ├── routing.py              # Routing distance/time
  │   ├── weather.py              # Weather forecast
  │   ├── expenses.py             # Expense queries
  │   └── currency.py             # Currency conversion
```

---

## 4. Tool Ownership Matrix

Each tool belongs to exactly one agent's execution scope or is granted through the explicit registry:

| Agent | Allowed Tools | Disallowed Tools | Rationale |
| :--- | :--- | :--- | :--- |
| **Web Agent** | `search`, `fetch`, `geocode` | Database repositories, itinerary mutations, expenses | Untrusted input sandboxing; solely responsible for finding & verifying places |
| **Plan Agent** | `catalog_places`, `routing` | Arbitrary URL fetch, expenses, live disruption injection | Builds structural schedule from vetted research & seeds |
| **Replan Agent**| `weather`, `disruption_injector`, `catalog_places` | Currency conversion, unrestricted web fetch | Evaluates physical disruptions and alternative replacements |
| **Chat Agent** | `catalog_places`, `routing`, `expenses`, `currency` | Raw web search, arbitrary web fetch, direct DB write | Conversational assistance; proposes modifications via proposals only |

---

## 5. Public Contract Preservation

1. **Gateway Functions (`gateway.py`)**: Signatures of `run_plan`, `run_replan`, `resume_replan`, and `run_chat` remain 100% unchanged.
2. **Event Types (`events.py`)**: All 10 `AgentEvent` types (`step`, `tool_call`, `tool_result`, `llm_call`, `draft`, `disruption`, `proposal`, `proposal_update`, `error`, `done`) are preserved. Nodes emit events with their qualified name (e.g. `web_agent.search`, `planner.draft`).
3. **Deterministic Verification**: Pydantic models in `state.py` and validator rules in `rules/validator_rules.py` remain pure functions.
4. **Human Approval (`interrupt()`)**: Neither the Chat Agent nor the Replan Agent writes itinerary changes directly; all modifications require explicit approval via `interrupt()`.
