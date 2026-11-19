# Reroute

> **An agentic AI travel planner that builds your itinerary, monitors it, and proposes smart replans when things change (weather, closures, delays, budget overruns). The user approves or rejects every change.**

---

## Repository Structure

```
reroute/
├── docs/                             # System specifications & architecture
│   ├── 01_PRD.md                     # Product requirements & user journeys
│   ├── 02_UX_DESIGN.md               # Design principles, screen layouts, and interaction patterns
│   ├── 03_ARCHITECTURE.md            # System architecture, event schemas, and data flow
│   ├── 04_schema.sql                 # PostgreSQL relational database schema
│   └── 05_API_AND_AGENT_CONTRACT.md  # REST API specifications, SSE event stream schema
├── frontend/                         # Next.js 14 Web Application
│   ├── src/                          # TypeScript source (components, hooks, pages, styles)
│   ├── tests/                        # Playwright E2E and Axe accessibility test suites
│   ├── screenshots/                  # Route & feature screenshots
│   ├── STRESS_TEST_REPORT.md         # Full stress testing, hardening & QA report
│   ├── DECISIONS.md                  # Implementation decisions log
│   ├── DESIGN_CHANGES.md             # Visual design and ergonomics log
│   ├── COLOR_CHANGES.md              # Theme and color token specification
│   ├── package.json                  # Dependencies and scripts
│   └── README.md                     # Frontend setup and developer documentation
├── STRESS_TEST_REPORT.md             # Top-level QA & stress test report
└── LICENSE                           # MIT License
```

---

## Getting Started

### Prerequisites
- Node.js >= 18.0.0
- npm >= 9.0.0

### Running the Frontend
The frontend runs self-contained out-of-the-box using an in-memory MSW mock layer:

```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to view the application.

### Running Quality and Stress Verification

```bash
cd frontend

# Run type checker
npx tsc --noEmit

# Run ESLint
npm run lint

# Run Vitest test suite (41 tests)
npm test

# Build production bundle
npm run build

# Run Playwright cross-browser and accessibility suite (40 tests across Chromium, Firefox, WebKit, Mobile Chrome)
npm run test:e2e
```

Refer to [STRESS_TEST_REPORT.md](./STRESS_TEST_REPORT.md) for detailed test metrics, resilience benchmarks, and root-cause fix analyses.
