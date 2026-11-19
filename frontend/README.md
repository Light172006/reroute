# Reroute — Frontend Application

> **"A trip plan that fixes itself."**
> Reroute builds your itinerary, continuously monitors it against live weather, closures, delays, and budget overruns, and proposes smart replans when disruptions occur. Every change requires human-in-the-loop approval.

---

## 1. Quick Start

### Prerequisites
- Node.js >= 18.0.0 (tested on Node v20/v24)
- npm >= 9.0.0

### Installation
```bash
cd frontend
npm install
```

### Running the App (Mock Mode — Zero Backend Required)
By default, the application runs fully functional in mock mode with seed trips, mock SSE streams, interactive Leaflet maps, and real-time disruption simulation:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 2. Environment Variables & Backend Integration

The frontend reads configuration from `.env.local`:

| Variable | Default Value | Description |
|---|---|---|
| `NEXT_PUBLIC_USE_MOCKS` | `true` | When `true`, uses the in-memory MSW mock store and simulated SSE streams. |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Base URL of the FastAPI backend when mocks are disabled. |

### Switching to the Real Backend
1. In `.env.local`, set:
   ```env
   NEXT_PUBLIC_USE_MOCKS=false
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```
2. Ensure your FastAPI backend is running on `http://localhost:8000`.
3. Restart the Next.js development server:
   ```bash
   npm run dev
   ```

---

## 3. Tech Stack

- **Framework:** Next.js 14 (App Router) + TypeScript (strict mode)
- **Styling & Tokens:** Tailwind CSS + custom design tokens
- **Icons:** `lucide-react` (stroke width 1.75, consistent sizing)
- **Server State:** TanStack Query v5 (React Query)
- **UI State:** Zustand (for small transient UI state)
- **Forms & Validation:** `react-hook-form` + `zod`
- **Interactive Maps:** Leaflet + react-leaflet with OpenStreetMap tiles
- **Drag & Drop:** `@dnd-kit/core` + `@dnd-kit/sortable`
- **Real-Time Streaming:** `@microsoft/fetch-event-source` + native SSE
- **Dark Mode:** `next-themes` (light and dark mode with WCAG AA compliance)
- **Testing:** Vitest + React Testing Library (unit/stress tests) + Playwright (cross-browser E2E and Axe audits)

---

## 4. Verification & Testing

```bash
# Type check
npx tsc --noEmit

# Lint
npm run lint

# Unit & Stress tests (Vitest)
npm test

# Build production bundle
npm run build

# End-to-end and Axe accessibility tests (Playwright)
npm run test:e2e
```

---

## 5. Documentation & Reports

- [STRESS_TEST_REPORT.md](./STRESS_TEST_REPORT.md): Comprehensive stress test, resilience audit, and bug fix report.
- [DECISIONS.md](./DECISIONS.md): Architectural and UX implementation decisions.
- [DESIGN_CHANGES.md](./DESIGN_CHANGES.md): Visual hierarchy, typography, and polish documentation.
- [COLOR_CHANGES.md](./COLOR_CHANGES.md): Color tokens and high-contrast dashboard implementation.
