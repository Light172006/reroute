# Architectural and Design Decisions (DECISIONS.md)

This log documents key technical choices and trade-offs made in the `reroute_agents` package.

---

## Decision 1: Pure Functions for Deterministic Validation and Impact Analysis
- **Context:** Travel itineraries require strict constraint satisfaction (opening hours, travel times, budget caps, altitude acclimatization). LLMs frequently hallucinate feasibility or overlook mathematical constraints.
- **Decision:** The Validator and Impact Analyzer are implemented as pure, deterministic Python functions with zero external I/O or LLM calls.
- **Consequence:** The LLM only proposes itineraries and substitutions; deterministic code decides whether they are valid. The validation loop in `plan_graph` is bounded to at most 3 iterations.

## Decision 2: In-Memory Repositories alongside Protocol Interfaces
- **Context:** The agent system must be tested without requiring a running PostgreSQL database, and must be runnable via a self-contained CLI.
- **Decision:** All persistence boundaries are formalized as typing Protocols (`interfaces.py`). High-performance in-memory implementations (`in_memory.py`) are provided for testing and CLI execution. Production adapters wrap SQLAlchemy AsyncSession without altering the agent's core logic.
- **Consequence:** 100% test isolation, fast test suite execution, and clean decoupling from database drivers.

## Decision 3: Regional Extensibility without Contract Breakage
- **Context:** Himalayan and North-East destinations present unique operational challenges: altitude sickness risk, restricted area permits (ILP/PAP/RAP), seasonal snow/monsoon road closures, and prolonged mountain road travel times.
- **Decision:** Model regional specifics through `places.raw` metadata and map regional validation errors into the existing `Violation.code` values (`day_too_long` for rapid altitude climb, `closed` for seasonal access and permit office closures). Disruptions are mapped into existing `DisruptionEvent.type` values.
- **Consequence:** Zero breaking changes to the REST API, SSE event streams, or database schema. Full compatibility with existing frontend expectations.

## Decision 4: Tier-Based LLM Gateway with Resilient Fallback Chains
- **Context:** Free-tier LLMs (Gemini, Groq) may encounter rate limits (HTTP 429), temporary outages (5xx), or formatting failures.
- **Decision:** Models are organized into tiers (`strong`, `small`, `local`). Each tier has a configurable chain of providers (e.g., `gemini:gemini-2.5-flash,groq:llama-3.3-70b-versatile`). Tenacity backoff with jitter and token bucket rate limiting are applied. On unrecoverable failure, execution falls back to the next provider, emitting an `llm_call` event with `payload.fallback = true`.
- **Consequence:** High reliability during live demos and automated evaluations, even when one provider is rate-limited.

## Decision 5: Non-Destructive Replanning and Proposal Diffing
- **Context:** Travelers find it disorienting when an entire trip changes because of a single rainy afternoon.
- **Decision:** The replanner modifies only items affected by disruptions. Unaffected items and user-locked items are preserved byte-identical. Changes are diffed against the parent version, producing an explicit human-readable diff (`replace`, `add`, `remove`, `move`).
- **Consequence:** Predictable, transparent modifications that travelers can easily inspect and approve.
