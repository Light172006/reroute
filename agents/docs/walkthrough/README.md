# Reroute Agent System: Complete Walkthrough and Visual Architecture

Welcome to the technical walkthrough documentation for the Reroute agentic system (`agents/reroute_agents/`). This directory contains comprehensive visual diagrams, architectural breakdowns, trace evidence, and presentation aids designed to explain and defend the agent system.

---

## Directory Index

| File / Directory | Purpose | Best For |
|---|---|---|
| **[FLOWCHARTS.md](file:///d:/reroute/agents/docs/walkthrough/FLOWCHARTS.md)** | Complete set of 14 Mermaid diagrams with legends, captions, reading guides, and a diagram-to-code traceability index. | Visual architecture review, board defense, examiner presentations |
| **[CODEBASE_WALKTHROUGH.md](file:///d:/reroute/agents/docs/walkthrough/CODEBASE_WALKTHROUGH.md)** | In-depth engineering walkthrough explaining every layer, function, rule threshold, configuration setting, and design rationale. | Deep code study, onboarding new engineers, technical defense |
| **[PRESENTER_CHEATSHEET.md](file:///d:/reroute/agents/docs/walkthrough/PRESENTER_CHEATSHEET.md)** | High-density reference aid containing the 30s/2min pitch, 10 exact facts with line numbers, 10 hard examiner questions & answers, and things not to claim. | Oral defense, live demos, quick recall during examinations |
| **[diagrams/](file:///d:/reroute/agents/docs/walkthrough/diagrams/)** | Rendered high-resolution vector SVGs and raster PNGs for all 14 diagrams (`01-master.svg` ... `14-slide-overview.png`). | Slides, PDF reports, projector presentations |
| **[traces/](file:///d:/reroute/agents/docs/walkthrough/traces/)** | Real, captured event stream traces (`01_plan_run.json` ... `05_chat_run.json`) demonstrating deterministic offline execution. | Verification evidence, worked examples, API payload inspection |

---

## Suggested Reading Order

1. **Start with the high-level concept**:
   Read Section 1 & 2 of `CODEBASE_WALKTHROUGH.md` ("What the Agent Package Is" and "The Agentic Cycle Explained").
2. **Review the visual architecture**:
   Open `FLOWCHARTS.md` and inspect Diagram 1 (Master Architecture), Diagram 2 (Plan Graph), and Diagram 3 (Replan Graph).
3. **Inspect the real-world traces**:
   Review `traces/02_replan_approve_run.json` to see how a real Day 2 rain disruption in Darjeeling moves through the 12 emitted events.
4. **Study the deep dive**:
   Read Section 5 of `CODEBASE_WALKTHROUGH.md` ("Deep Dive by Layer") alongside the source code in `agents/reroute_agents/`.
5. **Prepare for examination / presentation**:
   Review `PRESENTER_CHEATSHEET.md` to memorize the exact numbers, loop limits, and answers to challenging technical questions.

---

## How to Regenerate the Diagrams

All 14 diagrams are defined in Mermaid syntax in `FLOWCHARTS.md` and compiled using `@mermaid-js/mermaid-cli` (`mmdc`).

### Prerequisites
Node.js (v18+) with `npx`. No global npm package installation is necessary; `npx` downloads and caches `@mermaid-js/mermaid-cli` automatically.

### Automated Regeneration Script
To regenerate all 14 SVG and PNG diagrams in a single automated step:
```powershell
python agents/docs/walkthrough/build_walkthrough.py
```

### Manual Individual Commands
To manually re-render an individual diagram from its `.mmd` definition:
```powershell
# Example: Re-render Diagram 03 (Replan Graph)
npx -p @mermaid-js/mermaid-cli mmdc -i agents/docs/walkthrough/diagrams/mmd/03-replan-graph.mmd -o agents/docs/walkthrough/diagrams/03-replan-graph.svg
npx -p @mermaid-js/mermaid-cli mmdc -i agents/docs/walkthrough/diagrams/mmd/03-replan-graph.mmd -o agents/docs/walkthrough/diagrams/03-replan-graph.png
```

---

## Verification and Source Code Truth

Every flowchart node, line number reference, and rule threshold in these documents has been verified against the live Python codebase in `agents/reroute_agents/`. All 126 unit, integration, and stress tests pass with 91% code coverage.
