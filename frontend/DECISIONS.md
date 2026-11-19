# Reroute: Frontend Architecture & Design Decisions

This document records the architectural and design choices made where details were unspecified in `02_UX_DESIGN.md` and `05_API_AND_AGENT_CONTRACT.md`. All choices adhere strictly to the core principles: **Calm under change**, **Always explain**, **User in control**, and **Glanceable**.

---

### 1. Mock Architecture & Seamless Backend Switch
- **Decision:** Implemented a unified mock layer in `src/mocks/handlers.ts` and `src/lib/api.ts` coupled with `src/lib/sse.ts`.
- **Reason:** Developing a fully demoable IDP without an active backend requires realistic state mutations (creating trips, toggling locks, reordering items, approving/rejecting proposals, logging expenses, chatting).
- **Backend Switching:** Controlled via `NEXT_PUBLIC_USE_MOCKS=true|false`. When `false`, the client transparently routes all requests to `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000/api/v1`) and attaches JWT Bearer tokens with automatic 401 refresh handling.

### 2. SSE Streaming Simulation
- **Decision:** Built a reactive event dispatcher in `src/mocks/handlers.ts` and `src/lib/sse.ts`.
- **Reason:** In pure client-side demo runs, mock SSE events stream with 300ms intervals, allowing reviewers and viva examiners to observe live agent transitions: running spinners, completed ticks, and disruption alerts appearing in real time.

### 3. Cost & Time Delta Display Formatting
- **Decision:** Implemented `formatDeltaCurrency` in `src/lib/format.ts`.
- **Reason:** The spec in `02_UX_DESIGN.md` mandates `(+/- Rs)`. Decreases in cost appear as `-Rs 150` in success green, and increases as `+Rs 200` in danger red, supplemented by text labels ("Cost Delta") and directional icons (`TrendingDown`, `TrendingUp`) to fulfill WCAG AA guidelines (never relying on color alone).

### 4. Responsive Breakpoints & Mobile Workspace
- **Decision:**
  - **Desktop (>= 1024px):** 3 columns (Day Nav + Budget Bar on left, Day Itinerary + Summary in center, Agent Timeline + Chat on right).
  - **Tablet (768px - 1023px):** 2 columns (Day Nav + Itinerary, with collapsible Agent Panel).
  - **Mobile (< 768px):** Single column with horizontal scrolling day chips, a top disruption banner, and bottom tab navigation (`Itinerary` | `Map` | `Budget` | `Agent`).
  - **Review Sheet:** Renders as a centered modal on desktop and transforms into a bottom sheet on mobile screens.

### 5. Leaflet Integration & Client-Side Rendering
- **Decision:** Dynamically loaded Leaflet and OpenStreetMap tiles in `src/components/MapView.tsx` after client hydration.
- **Reason:** Prevents Next.js SSR `window is not defined` errors while rendering interactive numbered stop markers (1, 2, 3...) and route polylines. Stops affected by an active disruption are highlighted in amber (`#F59E0B`).

### 6. Drag-and-Drop Reordering with Constraint Protection
- **Decision:** Utilized `@dnd-kit/core` and `@dnd-kit/sortable` with distance activation constraint (5px).
- **Constraint Handling:** Any item with `is_locked: true` has its drag handle disabled and cannot be dragged. Agent replans are prevented from modifying locked items.

### 7. Version Diffing
- **Decision:** Diffs match items across versions using their `stable_key`.
- **Visuals:** Red strikethrough with a minus icon for removed items; green highlight with a plus icon for proposed replacements; unchanged items greyed out; locked items annotated with a lock badge.

---
