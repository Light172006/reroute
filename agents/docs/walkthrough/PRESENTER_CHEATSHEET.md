# Reroute Agent: Presenter and Defender Cheatsheet

This reference sheet is designed for presenting and defending the Reroute agent architecture before technical examiners, stakeholders, or system architects. Every fact, number, and defense is backed by verified code in `agents/reroute_agents/`.

---

## 1. The Agentic Cycle

### The 30-Second Elevator Pitch
"Reroute is an autonomous travel intelligence engine that monitors active trips against real-world disruptions—like mountain landslides or monsoons—and generates minimal, conflict-free itinerary replans. Our core design principle is **deterministic gatekeeping**: an LLM proposes creative substitutions, but pure Python rules decide whether a schedule is physically feasible, and no change is ever committed without explicit traveler approval via LangGraph's `interrupt()` primitive."

### The 2-Minute Deep Technical Explanation
"Most travel planners fail because they are static or rely on probabilistic LLMs to validate physical constraints, leading to hallucinations like overlapping stops, altitude sickness, or budget overruns. Reroute implements a 7-stage closed control loop:
1. **Sense**: A periodic monitor ingests real-time weather, transit, and expense signals. Crucially, the monitor runs with zero LLM calls, keeping idle operational costs at zero.
2. **Analyze**: Pure deterministic rules match environmental signals against scheduled itinerary items. Disrupted items are hashed into a deterministic SHA-256 fingerprint to prevent duplicate replan loops.
3. **Propose**: An LLM (via our resilient multi-provider fallback chain: Gemini -> Groq -> Ollama) proposes targeted substitutions for affected stops while keeping locked items byte-identical.
4. **Verify**: Pure Python validator rules enforce operating hours, minimum 30-minute travel buffers, daily pace limits, and high-altitude ascent caps (>1,200m/day).
5. **Decide**: The graph executes LangGraph's `interrupt()` primitive, pausing execution and saving state to a persistent checkpointer. The traveler reviews a clear visual diff (stops changed, cost delta).
6. **Act**: When the traveler clicks Approve, `resume_replan` loads the checkpoint and increments the itinerary to version v(N+1). If rejected, the previous version is preserved unchanged.
7. **Watch**: The background monitor returns to quiescent tracking of upcoming stops."

---

## 2. Ten Exact Facts from the Code

| # | Fact | Exact Number | Source File and Line |
|---|---|---|---|
| **1** | Plan Graph Loop Limit | **3 iterations max** | `agents/reroute_agents/config.py:L87` (`max_plan_iterations`) |
| **2** | Replan Graph Loop Limit | **2 iterations max** | `agents/reroute_agents/config.py:L88` (`max_replan_iterations`) |
| **3** | Chat Tool Loop Limit | **5 iterations max** | `agents/reroute_agents/config.py:L89` (`max_chat_iterations`) |
| **4** | Rain Disruption Threshold | **Precipitation probability >= 60%** (default 0.60; tests use 0.70) | `agents/reroute_agents/config.py:L82` (`precip_prob_threshold`) |
| **5** | Cascading Delay Threshold | **>= 30 minutes** | `agents/reroute_agents/config.py:L83` (`delay_threshold_minutes`) |
| **6** | Budget Overrun Threshold | **>= 10% overrun** | `agents/reroute_agents/config.py:L84` (`budget_overrun_pct_threshold`) |
| **7** | High-Altitude Acclimatization Threshold | **> 1,200m ascent / 3,000m baseline** | `agents/reroute_agents/rules/altitude.py:L16`, `config.py:L61` |
| **8** | Seed Places Catalog Size | **62 verified places** across 4 regions | `agents/data/seed/` (`ladakh:16`, `darjeeling:16`, `sikkim:15`, `arunachal:15`) |
| **9** | Total Graph Nodes | **15 nodes total** (Plan: 6, Replan: 6, Chat: 3) | `graphs/plan_graph.py`, `replan_graph.py`, `chat_graph.py` |
| **10** | Test Suite Verification | **126 tests passing, 0 failures, 91% coverage** | `agents/tests/` (verified via `pytest`) |

---

## 3. Ten Hardest Examiner Questions and Answers

### Q1: "Why did you use LangGraph instead of a standard LangChain agent or AutoGen?"
**Answer**: "LangGraph models state transitions as a formal directed graph with explicit state reducers and checkpointers. Crucially, it provides native support for `interrupt()`. This enables true Human-in-the-Loop workflows where the agent pauses mid-execution, serializes state to storage under a persistent `thread_id`, and resumes seamlessly when an HTTP request arrives minutes or hours later. AutoGen and standard chains do not provide this deterministic, durable pause-and-resume model."
*Evidence*: `agents/reroute_agents/nodes/build_proposal.py:L94` and `agents/reroute_agents/gateway.py:L261`.

### Q2: "What prevents the agent from getting stuck in an infinite fix loop when constraints cannot be satisfied?"
**Answer**: "Every cycle in our state graphs has a strict deterministic iteration counter stored in graph state. In `plan_graph`, `iteration` is capped at 3 (`max_plan_iterations`). If a plan cannot be reconciled after 3 iterations, the graph routes directly to `finalize_node`, which logs the unresolved items as non-blocking flags rather than stalling. In `replan_graph`, the limit is 2 iterations."
*Evidence*: `agents/reroute_agents/graphs/plan_graph.py:L27-L29` and `agents/reroute_agents/config.py:L87-L89`.

### Q3: "How do you guarantee that an LLM hallucination won't book a hotel over an existing activity or exceed the budget?"
**Answer**: "The LLM has zero authority to commit itineraries or decide validity. After the LLM outputs a draft, `validator_node` runs pure, deterministic Python functions. It mathematically compares start/end times for overlaps, measures travel buffers against OSRM matrices, sums costs against `spec.budget_total`, and inspects operating hours. If any check fails, the draft is rejected and sent back for repair."
*Evidence*: `agents/reroute_agents/rules/validator_rules.py:L18-L162`.

### Q4: "How does the system ensure unaffected stops are not altered during a replan?"
**Answer**: "Our replanner prompt and substitution logic explicitly isolate affected stops using the disruption event's `affected_item_ids`. Unaffected items and stops marked `locked=True` are merged back into the schedule byte-for-byte. Our regression test `test_replan_preserves_unaffected_items_byte_identical` mathematically verifies that all unimpacted items retain identical JSON representations."
*Evidence*: `agents/reroute_agents/nodes/replanner.py:L115-L135` and `tests/integration/test_invariants.py`.

### Q5: "If Gemini or Groq experiences an outage or rate limit (HTTP 429), does the entire system crash?"
**Answer**: "No. We built `ResilientLLMChain`, which implements a tiered fallback chain (`LLM_STRONG_CHAIN`). If the primary model (Gemini 2.5 Flash) fails after 2 exponential backoff retries, it automatically falls back to Groq Llama 3.3 70B, and then to a local Ollama instance. Every call is also governed by an in-memory `TokenBucketRateLimiter` (2.0 RPS, burst capacity 10) to prevent rate limits before they happen."
*Evidence*: `agents/reroute_agents/llm.py:L62-L233`.

### Q6: "What happens when an LLM returns malformed JSON that fails your Pydantic schema?"
**Answer**: "We do not crash or immediately switch providers. `ResilientLLMChain._invoke_with_repair` intercepts Pydantic validation errors and issues a 1-shot repair prompt containing the exact parsing error and the failed text, asking the model to fix its JSON syntax. If and only if the repair attempt also fails does the chain fail over to the secondary provider."
*Evidence*: `agents/reroute_agents/llm.py:L151-L188`.

### Q7: "How do you keep operational costs low if the monitor runs continuously across thousands of active trips?"
**Answer**: "The background monitor (`evaluate_trip`) executes zero LLM calls during quiescent monitoring. It fetches cached weather forecasts and transit signals, and evaluates them against pure deterministic impact rules (`analyze_disruptions()`). An LLM is only invoked when an actual disruption impacts an active stop and the traveler approves replanning."
*Evidence*: `agents/reroute_agents/monitor.py:L23-L88`.

### Q8: "How do you prevent 'replan storms' where the monitor repeatedly detects the same storm and triggers endless proposals?"
**Answer**: "We compute a deterministic SHA-256 fingerprint for every detected disruption using `trip_id`, `category`, `day_index`, and `item_id`. Before triggering a replan, `impact_analyzer_node` checks whether that fingerprint is already active in `disruptions` repository. Recurring signals with matching fingerprints are discarded."
*Evidence*: `agents/reroute_agents/rules/impact_rules.py:L233-L255` and `nodes/impact_analyzer.py:L45-L55`.

### Q9: "Can a user manipulate the chat assistant to bypass human approval and silently modify the database?"
**Answer**: "No. The chat tool `modify_itinerary_item` does not perform direct database mutations. Instead, it constructs a `ReplanProposal` in memory and sets `state['proposal']`. The proposal cannot be committed without going through the standard approval workflow. Adversarial prompt injection attacks cannot force a direct write because the tool does not possess write privileges to `itinerary_versions`."
*Evidence*: `agents/reroute_agents/graphs/chat_graph.py:L252-L291`.

### Q10: "What happens if an external tool like Open-Meteo or OSRM times out or returns a 500 error?"
**Answer**: "All tools are decorated with `@safe_tool`. The decorator enforces a 10-second timeout, executes a 3-attempt tenacity retry, and catches uncaught exceptions, returning a normalized dictionary `{'ok': False, 'error': str(e)}`. The agent graph treats this as a degraded signal and falls back to offline catalog distance estimates rather than failing."
*Evidence*: `agents/reroute_agents/tools/base.py:L24-L74`.

---

## 4. Things You Should NOT Claim

To maintain absolute credibility during an examination or technical defense, **never make the following claims**, because the code does not support them:

1. **Do NOT claim live worldwide GPS coverage**: The catalog currently contains 62 verified seed places across four Himalayan regions (Ladakh, Spiti, Darjeeling, Arunachal). Queries for Paris or Tokyo will not find places unless new seed data is loaded.
2. **Do NOT claim live automated flight booking or hotel payment execution**: The system produces verified itinerary proposals and diffs; it does not interface with Sabre, Amadeus, or payment gateways.
3. **Do NOT claim the test suite ran on live Gemini API tokens in CI**: Automated tests run with `FakeLLM` and `MOCK_TOOLS=true` to guarantee zero-cost, deterministic execution. Live LLM testing requires passing real API keys and running `evaluation/run_eval.py --live`.
4. **Do NOT claim persistent multi-node Postgres clustering out of the box**: The default checkpointer and repositories are in-memory (`MemorySaver`, `InMemoryRepositories`). Postgres integration requires passing a connection string to `PostgresSaver`.
5. **Do NOT claim the chat graph has separate specialist sub-agents**: Chat is handled by a single ReAct loop (`chat_agent_node`) equipped with safe tools, not a multi-agent swarm.
