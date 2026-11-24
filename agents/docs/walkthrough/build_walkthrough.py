import subprocess
import sys
from pathlib import Path

diagrams_dir = Path("agents/docs/walkthrough/diagrams")
mmd_dir = diagrams_dir / "mmd"
mmd_dir.mkdir(parents=True, exist_ok=True)

diagrams = {
    "01-master": """
flowchart TD
  classDef stadium fill:#f4f4f5,stroke:#3f3f46,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef llmNode fill:#fef3c7,stroke:#d97706,stroke-width:2px;
  classDef toolNode fill:#fce7f3,stroke:#db2777,stroke-width:2px;
  classDef decisionNode fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;
  classDef humanNode fill:#ecfdf5,stroke:#059669,stroke-width:2px;
  classDef storageNode fill:#f3e8ff,stroke:#9333ea,stroke-width:2px;

  START([Trigger Sources: Plan / Replan / Chat / Monitor]):::stadium --> GW["Gateway Functions [gateway.py]"]:::codeNode

  GW --> PG["Plan Graph [plan_graph.py]"]:::codeNode
  GW --> RG["Replan Graph [replan_graph.py]"]:::codeNode
  GW --> CG["Chat Graph [chat_graph.py]"]:::codeNode

  PG --> LLM_GW("LLM Gateway [llm.py]"):::llmNode
  RG --> LLM_GW
  CG --> LLM_GW

  PG --> TOOLS{{"Tool Layer [tools/]"}}:::toolNode
  RG --> TOOLS
  CG --> TOOLS

  PG --> STO[("Repositories and Checkpointer")]:::storageNode
  RG --> STO
  CG --> STO

  PG --> EVT["Typed AgentEvent Stream"]:::codeNode
  RG --> EVT
  CG --> EVT

  subgraph BE ["Backend (not part of agents/)"]
    API_OUT["FastAPI SSE and HTTP Routers"]
  end

  EVT -.-> API_OUT
""",

    "02-plan-graph": """
flowchart TD
  classDef stadium fill:#f4f4f5,stroke:#3f3f46,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef llmNode fill:#fef3c7,stroke:#d97706,stroke-width:2px;
  classDef toolNode fill:#fce7f3,stroke:#db2777,stroke-width:2px;
  classDef decisionNode fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;

  START([START]):::stadium --> INTAKE["Validate Trip Spec [intake_node]"]:::codeNode
  INTAKE --> RESEARCH{{"Search Catalog Places [researcher_node]"}}:::toolNode
  RESEARCH --> PLANNER("Draft Day-by-Day Itinerary [planner_node]"):::llmNode
  PLANNER --> VALIDATE["Execute Pure Rules [validator_node]"]:::codeNode

  VALIDATE --> COND_VAL{"Violations Exist? [route_after_validator]"}:::decisionNode
  COND_VAL -- "Issues and Iter less than 3" --> PLANNER
  COND_VAL -- "Issues and Iter at 3 (Cap)" --> FINALIZE["Persist Version and Flag Issues [finalize_node]"]:::codeNode
  COND_VAL -- "No Violations" --> BUDGET["Audit Cost and Daily Limits [budget_check_node]"]:::codeNode

  BUDGET --> COND_BUD{"Budget OK? [route_after_budget]"}:::decisionNode
  COND_BUD -- "Overrun and Iter less than 3" --> PLANNER
  COND_BUD -- "Passed or Iter at 3" --> FINALIZE

  FINALIZE --> END_NODE([END: Initial Itinerary v1]):::stadium
""",

    "03-replan-graph": """
flowchart TD
  classDef stadium fill:#f4f4f5,stroke:#3f3f46,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef llmNode fill:#fef3c7,stroke:#d97706,stroke-width:2px;
  classDef toolNode fill:#fce7f3,stroke:#db2777,stroke-width:2px;
  classDef decisionNode fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;
  classDef humanNode fill:#ecfdf5,stroke:#059669,stroke-width:2px;

  START([START]):::stadium --> SIGNALS{{"Fetch Weather and Expenses [collect_signals_node]"}}:::toolNode
  SIGNALS --> IMPACT["Match Disruptions and Fingerprint [impact_analyzer_node]"]:::codeNode
  IMPACT --> COND_IMP{"Disruptions Found? [route_after_impact]"}:::decisionNode

  COND_IMP -- "No Disruptions" --> END_NOOP([END: Itinerary Unchanged]):::stadium
  COND_IMP -- "Disruptions Found" --> REPLAN("Generate Targeted Replacements [replanner_node]"):::llmNode

  REPLAN --> VAL["Validate Substitution Rules [validator_node]"]:::codeNode
  VAL --> COND_VAL{"Valid Proposal? [route_after_validator]"}:::decisionNode
  COND_VAL -- "Violations and Iter less than 3" --> REPLAN
  COND_VAL -- "Valid or Iter at 3" --> PROPOSAL["Build Diff and Interrupt HITL [build_proposal_node]"]:::codeNode

  PROPOSAL --> DECISION[/"Traveler Decision: Approve or Reject or Alternatives"/]:::humanNode
  DECISION --> APPLY["Apply or Discard Proposal [apply_changes_node]"]:::codeNode

  APPLY --> COND_DEC{"Decision Type [route_after_decision]"}:::decisionNode
  COND_DEC -- "Approve" --> END_APP([END: Version Incremented to vN+1]):::stadium
  COND_DEC -- "Reject" --> END_REJ([END: Prior Version Preserved]):::stadium
  COND_DEC -- "Alternatives and Iter less than 3" --> REPLAN
  COND_DEC -- "Alternatives and Iter at 3" --> END_REJ
""",

    "04-chat-graph": """
flowchart TD
  classDef stadium fill:#f4f4f5,stroke:#3f3f46,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef llmNode fill:#fef3c7,stroke:#d97706,stroke-width:2px;
  classDef toolNode fill:#fce7f3,stroke:#db2777,stroke-width:2px;
  classDef decisionNode fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;

  START([START]):::stadium --> CHAT("Evaluate Query and Select Tool [chat_agent_node]"):::llmNode
  CHAT --> ROUTE{"Has Tool Call? [route_after_chat_agent]"}:::decisionNode

  ROUTE -- "Tool Call and Iter less than 5" --> TOOLS{{"Execute Safe Tool: Places, Route, or Itinerary [tools_node]"}}:::toolNode
  TOOLS --> CHAT

  ROUTE -- "Mutation Attempt" --> PROP["Draft Proposal Only: No Direct DB Write [tools_node]"]:::codeNode
  PROP --> CHAT

  ROUTE -- "Final Answer or Iter at 5" --> FINALIZE["Emit Tokens and Messages [finalize_node]"]:::codeNode
  FINALIZE --> END_NODE([END]):::stadium
""",

    "05-hitl-sequence": """
sequenceDiagram
  autonumber
  actor User as Traveler
  participant FE as Frontend UI
  participant BE as Backend API
  participant GW as Gateway [gateway.py]
  participant RG as Replan Graph [replan_graph.py]
  participant CP as Checkpointer [checkpointer.py]

  User->>FE: Report disruption or trigger monitor
  FE->>BE: POST /trips/{id}/replan
  BE->>GW: run_replan(run_id, trip_id)
  GW->>RG: astream(initial_state)
  RG->>GW: emit disruption_event and proposal_event
  GW-->>BE: SSE stream (proposal ready)
  BE-->>FE: Render visual diff (cost, items changed)
  RG->>CP: interrupt() saves state to thread_id
  Note over RG,CP: Execution suspended. No changes committed.

  User->>FE: Submit decision (approve / reject / alternatives)
  FE->>BE: POST /trips/{id}/replan/resume
  BE->>GW: resume_replan(run_id, decision)
  GW->>CP: Load suspended state by thread_id
  GW->>RG: astream(Command(resume={decision}))
  RG->>RG: apply_changes_node (updates version on approve)
  RG->>GW: emit done_event
  GW-->>BE: SSE stream (done)
  BE-->>FE: Render updated itinerary v(N+1)
""",

    "06-event-timeline": """
flowchart TD
  classDef stadium fill:#f4f4f5,stroke:#3f3f46,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef llmNode fill:#fef3c7,stroke:#d97706,stroke-width:2px;
  classDef toolNode fill:#fce7f3,stroke:#db2777,stroke-width:2px;
  classDef humanNode fill:#ecfdf5,stroke:#059669,stroke-width:2px;

  subgraph PLAN_EVENTS ["Plan Stream: 18 Real Events"]
    P1["step: intake"]:::codeNode --> P2{{"tool_call and tool_result: researcher"}}:::toolNode
    P2 --> P3("step and draft: planner iter 1"):::llmNode
    P3 --> P4["step: validator 4 issues"]:::codeNode
    P4 --> P5("step and draft: planner iter 2"):::llmNode
    P5 --> P6["step: validator 4 issues"]:::codeNode
    P6 --> P7("step and draft: planner iter 3"):::llmNode
    P7 --> P8["step: validator cap reached"]:::codeNode
    P8 --> P9["step: finalize v1"]:::codeNode
    P9 --> P10([done: completed]):::stadium
  end

  subgraph REPLAN_EVENTS ["Replan Stream: 12 Real Events"]
    R1{{"step: collect_signals"}}:::toolNode --> R2["disruption: rain Day 2"]:::codeNode
    R2 --> R3("step: replanner substitution"):::llmNode
    R3 --> R4["step: validator passed"]:::codeNode
    R4 --> R5["proposal: ready for review"]:::codeNode
    R5 --> R6[/"PAUSE: interrupt HITL"/]:::humanNode
    R6 --> R7["step: resumed approve"]:::codeNode
    R7 --> R8["step: apply_changes updated v2"]:::codeNode
    R8 --> R9([done: completed]):::stadium
  end
""",

    "07-llm-fallback": """
flowchart TD
  classDef stadium fill:#f4f4f5,stroke:#3f3f46,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef llmNode fill:#fef3c7,stroke:#d97706,stroke-width:2px;
  classDef decisionNode fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;

  START([LLM Request]):::stadium --> LIM["Token Bucket Rate Limiter [llm.py]"]:::codeNode
  LIM --> CALL("Primary Model Call: Gemini [_invoke_with_retry]"):::llmNode

  CALL --> CHK{"Call Succeeded?"}:::decisionNode
  CHK -- "Rate Limit or Timeout" --> RETRY["Retry with Backoff max 2"]:::codeNode
  RETRY --> CALL
  CHK -- "5xx or Exhausted" --> NEXT("Fallback Provider: Groq [ResilientLLMChain]"):::llmNode

  CHK -- "HTTP 200" --> PARSE{"Parse Pydantic Schema"}:::decisionNode
  PARSE -- "Schema Error" --> REPAIR("1-Shot Schema Repair Prompt [_invoke_with_repair]"):::llmNode
  REPAIR --> PARSE2{"Repair OK?"}:::decisionNode
  PARSE2 -- "Failed" --> NEXT
  PARSE2 -- "Success" --> SUCCESS([Return Structured Object]):::stadium
  PARSE -- "Success" --> SUCCESS
  NEXT --> SUCCESS
""",

    "08-tool-wrapper": """
flowchart TD
  classDef stadium fill:#f4f4f5,stroke:#3f3f46,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef toolNode fill:#fce7f3,stroke:#db2777,stroke-width:2px;
  classDef decisionNode fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;
  classDef storageNode fill:#f3e8ff,stroke:#9333ea,stroke-width:2px;

  START([Tool Call]):::stadium --> MOCK{"Mock Tools Active?"}:::decisionNode
  MOCK -- "MOCK_TOOLS=true" --> RET_MOCK["Return Canned Seed Data [base.py]"]:::codeNode

  MOCK -- "Live Mode" --> CHK_CACHE[("Check In-Memory Cache [cache.py]")]:::storageNode
  CHK_CACHE -- "Cache Hit" --> RET_CACHE["Return Cached Response TTL 3600s"]:::codeNode

  CHK_CACHE -- "Cache Miss" --> INJ{"Disruption Injected?"}:::decisionNode
  INJ -- "Yes" --> RET_INJ["Return Injected Signal Data [injector.py]"]:::codeNode

  INJ -- "No" --> CALL{{"Invoke Async API with 10s Timeout [safe_tool]"}}:::toolNode
  CALL --> RES{"Status Code 200?"}:::decisionNode
  RES -- "Network 5xx" --> RETRY["Tenacity Retry 3 Attempts"]:::codeNode
  RETRY --> CALL
  RES -- "Success" --> WRITE[("Store in Cache Repository")]:::storageNode
  WRITE --> OK([Return Normalized Payload]):::stadium
  RES -- "Exception" --> ERR["Normalize: ok=False, error=msg"]:::codeNode
  ERR --> OK
""",

    "09-validator-rules": """
flowchart TD
  classDef stadium fill:#f4f4f5,stroke:#3f3f46,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef decisionNode fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;

  START([validate_itinerary]):::stadium --> R1["1. Check Overlaps [overlap]"]:::codeNode
  R1 --> R2["2. Check 30m Travel Gaps [travel_gap]"]:::codeNode
  R2 --> R3["3. Check Opening Hours [opening_hours]"]:::codeNode
  R3 --> R4["4. Check Budget Total and Daily Cap [budget_total]"]:::codeNode
  R4 --> R5["5. Check Locked Items Unchanged [locked_item_modified]"]:::codeNode
  R5 --> R6["6. Check Pace Stops/Day [pace_exceeded]"]:::codeNode
  R6 --> R7["7. Check Altitude Delta > 1200m [altitude_jump]"]:::codeNode
  R7 --> R8["8. Check High Mountain Passes [pass_closed]"]:::codeNode
  R8 --> R9["9. Check Restricted Area Permits [permit_missing]"]:::codeNode
  R9 --> CHK{"Violations List Empty?"}:::decisionNode
  CHK -- "Yes" --> PASS([Valid Itinerary]):::stadium
  CHK -- "No" --> FAIL([Return list of Violation objects]):::stadium
""",

    "10-impact-rules": """
flowchart TD
  classDef stadium fill:#f4f4f5,stroke:#3f3f46,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef decisionNode fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;
  classDef storageNode fill:#f3e8ff,stroke:#9333ea,stroke-width:2px;

  START([analyze_disruptions]):::stadium --> INGEST["Ingest Weather and Transit Signals"]:::codeNode
  INGEST --> R_RAIN{"Rain Prob >= 70%?"}:::decisionNode
  R_RAIN -- "Yes" --> EV_RAIN["Flag Outdoor Stops [weather_rain]"]:::codeNode

  INGEST --> R_SNOW{"Snow >= 5cm or Vis < 500m?"}:::decisionNode
  R_SNOW -- "Yes" --> EV_SNOW["Flag High-Altitude Passes [weather_snow]"]:::codeNode

  INGEST --> R_CLOSE{"Venue or Road Closure?"}:::decisionNode
  R_CLOSE -- "Yes" --> EV_CLOSE["Flag Place as Closed [closure]"]:::codeNode

  INGEST --> R_DELAY{"Transit Delay >= 30 mins?"}:::decisionNode
  R_DELAY -- "Yes" --> EV_DELAY["Flag Cascading Schedule Delays [transit_delay]"]:::codeNode

  INGEST --> R_BUD{"Expenses Overrun >= 15%?"}:::decisionNode
  R_BUD -- "Yes" --> EV_BUD["Flag Budget Overrun [budget_overrun]"]:::codeNode

  EV_RAIN --> FP["Compute SHA-256 Fingerprint [compute_disruption_fingerprint]"]:::codeNode
  EV_SNOW --> FP
  EV_CLOSE --> FP
  EV_DELAY --> FP
  EV_BUD --> FP

  FP --> DEDUP[("Deduplicate Against disruptions Repo")]:::storageNode
  DEDUP --> EMIT([Emit DisruptionEvent and Affected Item IDs]):::stadium
""",

    "11-monitor-flow": """
flowchart TD
  classDef stadium fill:#f4f4f5,stroke:#3f3f46,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef toolNode fill:#fce7f3,stroke:#db2777,stroke-width:2px;
  classDef decisionNode fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;
  classDef storageNode fill:#f3e8ff,stroke:#9333ea,stroke-width:2px;

  START(["evaluate_trip [monitor.py]"]):::stadium --> LOAD[("Load Trip and Active Itinerary [repos]")]:::storageNode
  LOAD --> WEATH{{"Fetch Live Weather via WeatherTool [tools/weather.py]"}}:::toolNode
  WEATH --> EXP{{"Fetch Total Incurred Expenses [tools/expenses.py]"}}:::toolNode
  EXP --> RULES["Execute Pure Rules [analyze_disruptions]"]:::codeNode

  RULES --> CHECK{"Unresolved Disruptions Found?"}:::decisionNode
  CHECK -- "No Impact" --> NOOP(["Return None: Zero LLM Cost"]):::stadium
  CHECK -- "Impact Detected" --> SAVE[("Save Disruption Record [repos.disruptions]")]:::storageNode
  SAVE --> REPLAN["Trigger Replan Run [gateway.run_replan]"]:::codeNode
  REPLAN --> DONE(["Replan Stream Started"]):::stadium
""",

    "12-data-model": """
flowchart LR
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef storageNode fill:#f3e8ff,stroke:#9333ea,stroke-width:2px;

  TripSpec["TripSpec: Pydantic"]:::codeNode --> ItineraryDraft["ItineraryDraft: Pydantic"]:::codeNode
  ItineraryDraft --> DraftItem["DraftItem: Pydantic"]:::codeNode
  DraftItem --> Violation["Violation: Pydantic"]:::codeNode
  DraftItem --> DisruptionEvent["DisruptionEvent: Pydantic"]:::codeNode

  ReplanProposal["ReplanProposal: Pydantic"]:::codeNode --> DiffItem["DiffItem: Pydantic"]:::codeNode
  ReplanProposal --> DraftItem

  PlanState[("PlanState: TypedDict")]:::storageNode --> TripSpec
  PlanState --> DraftItem
  PlanState --> Violation
  PlanState --> AgentEvent["AgentEvent: Pydantic"]:::codeNode

  ReplanState[("ReplanState: TypedDict")]:::storageNode --> ReplanProposal
  ReplanState --> DisruptionEvent
  ReplanState --> AgentEvent
""",

    "13-module-dependencies": """
flowchart TD
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef storageNode fill:#f3e8ff,stroke:#9333ea,stroke-width:2px;
  classDef toolNode fill:#fce7f3,stroke:#db2777,stroke-width:2px;
  classDef llmNode fill:#fef3c7,stroke:#d97706,stroke-width:2px;

  API["api.py"]:::codeNode --> GW["gateway.py"]:::codeNode
  MON["monitor.py"]:::codeNode --> GW

  GW --> GRAPHS["graphs/ plan, replan, chat"]:::codeNode
  GW --> REPOS[("repositories/ in_memory, interfaces")]:::storageNode
  GW --> CHK[("checkpointer.py")]:::storageNode

  GRAPHS --> NODES["nodes/ planner, validator, replanner"]:::codeNode
  GRAPHS --> TOOLS{{"tools/ weather, routing, places"}}:::toolNode

  NODES --> RULES["rules/ validator, impact, altitude"]:::codeNode
  NODES --> LLM("llm.py ResilientLLMChain"):::llmNode
  TOOLS --> TOOLS_BASE["tools/base.py safe_tool"]:::codeNode
  RULES --> STATE["state.py Pydantic Models and States"]:::codeNode
""",

    "14-slide-overview": """
flowchart LR
  classDef toolNode fill:#fce7f3,stroke:#db2777,stroke-width:2px;
  classDef codeNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
  classDef llmNode fill:#fef3c7,stroke:#d97706,stroke-width:2px;
  classDef humanNode fill:#ecfdf5,stroke:#059669,stroke-width:2px;

  SENSE["1. SENSE<br/>Collect live weather, road closures, expenses"]:::toolNode --> ANALYZE["2. ANALYZE<br/>Map disruptions to stops via pure deterministic rules"]:::codeNode
  ANALYZE --> PROPOSE["3. PROPOSE<br/>Autonomous LLM generates minimal substitutions"]:::llmNode
  PROPOSE --> VERIFY["4. VERIFY<br/>Deterministic rules audit hours, gaps, pace, altitude"]:::codeNode
  VERIFY --> DECIDE[/"5. HUMAN DECISION<br/>Traveler Approves, Rejects, or Asks Alternatives"/]:::humanNode
  DECIDE --> ACT["6. ACT<br/>Land new itinerary version upon approval"]:::codeNode
  ACT --> WATCH["7. WATCH<br/>Background monitor checks signals with 0 LLM cost"]:::codeNode
  WATCH -.-> SENSE
"""
}

def main():
    print(f"Total diagrams to process: {len(diagrams)}")
    for name, mmd in diagrams.items():
        mmd_path = mmd_dir / f"{name}.mmd"
        mmd_path.write_text(mmd.strip() + "\\n", encoding="utf-8")
        svg_path = diagrams_dir / f"{name}.svg"
        png_path = diagrams_dir / f"{name}.png"

        if svg_path.exists() and png_path.exists():
            print(f"Skipping {name} (already rendered)")
            continue

        print(f"Rendering {name}...")
        res_svg = subprocess.run(
            ["npx.cmd", "-p", "@mermaid-js/mermaid-cli", "mmdc", "-i", str(mmd_path), "-o", str(svg_path)],
            capture_output=True, text=True, shell=True
        )
        if res_svg.returncode != 0:
            print(f"Error rendering SVG {name}:\\nSTDOUT: {res_svg.stdout}\\nSTDERR: {res_svg.stderr}")
            sys.exit(1)

        res_png = subprocess.run(
            ["npx.cmd", "-p", "@mermaid-js/mermaid-cli", "mmdc", "-i", str(mmd_path), "-o", str(png_path)],
            capture_output=True, text=True, shell=True
        )
        if res_png.returncode != 0:
            print(f"Error rendering PNG {name}:\\nSTDOUT: {res_png.stdout}\\nSTDERR: {res_png.stderr}")
            sys.exit(1)

    print("SUCCESS: All 14 diagrams rendered to SVG and PNG successfully!")

if __name__ == "__main__":
    main()
