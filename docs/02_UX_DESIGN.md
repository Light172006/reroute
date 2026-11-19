# Reroute: UI/UX Design Spec

Responsive web app. Recommended frontend: **Next.js (React) + Tailwind CSS + shadcn/ui**, map via **Leaflet + OpenStreetMap** (free).

---

## 1. Design Principles

1. **Calm under change.** Disruptions should feel handled, not alarming.
2. **Always explain.** Every agent action is visible and has a reason.
3. **User in control.** Nothing changes without approval. Locked items stay locked.
4. **Glanceable.** A traveler on a phone should understand the day in 5 seconds.

## 2. Brand and Visual Language

| Token | Value |
|---|---|
| Primary | `#2563EB` (blue, trust, direction) |
| Accent | `#F59E0B` (amber, attention/disruption) |
| Success | `#16A34A` |
| Danger | `#DC2626` |
| Surface | `#FFFFFF` / dark `#0F172A` |
| Muted text | `#64748B` |
| Font | Inter (UI), JetBrains Mono (costs/times optional) |
| Radius | 12px cards, 8px inputs |
| Tone | Friendly, concise, never robotic ("Rain is coming Tuesday. Here's a swap.") |

Dark mode supported. Icons: lucide-react.

## 3. Information Architecture

```
/                       Landing
/login, /signup         Auth
/trips                  My trips (list)
/trips/new              Create trip wizard
/trips/[id]             Trip workspace (main screen)
   tabs: Itinerary | Map | Budget | Activity
/trips/[id]/versions    Version history + diff
/settings               Profile, units, currency
```

## 4. Key Screens

### 4.1 Landing
- Hero: "A trip plan that fixes itself." CTA: **Plan a trip**.
- 3 feature blocks: Plan, Watch, Reroute. A short looping demo of a replan.

### 4.2 My Trips
- Card grid: destination image, dates, status chip (`Draft`, `Planned`, `Needs attention`, `Active`, `Done`).
- "Needs attention" chip (amber) shows when a pending replan proposal exists.

### 4.3 Create Trip Wizard (3 steps, single page, progress bar)
1. **Where and when:** destination (autocomplete), start/end dates, group size.
2. **Budget:** total budget slider + currency, optional per-day cap.
3. **Vibe:** tag chips (Food, Culture, Nature, Nightlife, Shopping, Adventure), pace toggle (Relaxed / Balanced / Packed), notes textarea.
- Submit -> goes to the Trip Workspace in "Generating" state.

### 4.4 Trip Workspace (core screen)

**Desktop layout (3 columns):**

```
+--------------------------------------------------------------------------+
| Header: Trip name | dates | [Check my plan now] | [Simulate disruption v]  |
+----------------+-------------------------------------+-------------------+
| DAY NAV        | ITINERARY (selected day)            | AGENT PANEL       |
| Day 1          |  09:00 Victoria Memorial   Rs 100   |  Activity timeline|
| Day 2 (!)      |   v 15 min by taxi                  |  Chat input       |
| Day 3          |  10:30 Indian Museum  [lock]        |                   |
|                |  ...                                |                   |
| Budget bar     |  [Day summary: cost, walking, time] |                   |
+----------------+-------------------------------------+-------------------+
```

**Mobile:** single column. Bottom tab bar: Itinerary / Map / Budget / Agent. Day selector as horizontal scroll chips.

**Itinerary item card:**
- Time, title, category icon, duration, estimated cost.
- Travel-time connector line between cards (mode icon + minutes).
- Badges: `Outdoor`, `Weather risk`, `Closes 5pm`, `Locked`.
- Actions: lock/unlock, edit, remove, drag handle to reorder.

**Day navigation:** amber dot on a day with a pending disruption.

### 4.5 Disruption Banner and Replan Proposal (key interaction)

Appears at top of workspace when a proposal exists:

```
[!] Rain expected Day 2, 2-6pm (80%)   2 outdoor stops affected
    [Review changes]
```

**Review modal / side sheet:**
- **Why:** one-line reason + data source chip (e.g. "Open-Meteo forecast").
- **Before / After diff:** left column removed (red strike), right column added (green), unchanged items greyed.
- **Impact:** cost delta (+/- Rs), time delta, items changed count.
- **Actions:** `Approve` (primary), `Reject`, `Show alternatives` (asks agent for 2 more options).
- Locked items shown with a lock icon and never in the diff.

### 4.6 Agent Panel
- **Activity timeline:** streamed steps with icons and status (running spinner, done tick, failed cross). Examples:
  - "Fetching weather forecast" (done)
  - "Found 4 indoor alternatives" (done)
  - "Checking opening hours" (running)
- **Chat:** input at bottom; examples as suggestion chips ("Make Day 2 more relaxed", "Add a street-food stop", "Cut Rs 2000").
- Collapsible on desktop; its own tab on mobile.

### 4.7 Map Tab
- Day route polyline with numbered markers. Click marker -> item card.
- Affected items highlighted amber during a pending proposal.

### 4.8 Budget Tab
- Planned vs actual donut + per-category bars (stay, food, transport, activities).
- Expense list with "Add expense" button.
- Warning chip when actual > planned by 10%.

### 4.9 Version History
- List of versions (v1, v2...) with reason ("Rain replan, Day 2") and timestamp.
- Select two versions -> diff view. Button: "Restore this version".

### 4.10 Demo Mode (important for viva)
- "Simulate disruption" dropdown: Rain on Day N, Attraction closed, Train delayed 2h, Budget overrun.
- Injects a mock event and runs the real replanning pipeline.

## 5. States and Edge Cases

| State | UI |
|---|---|
| Generating plan | Skeleton cards + live activity timeline |
| Agent error | Inline message + `Retry`; show partial plan if available |
| LLM rate-limited | "Taking longer than usual, switching model" toast |
| No disruptions | Green "Plan looks good. Last checked 10:42" |
| Over budget | Amber budget bar, banner with "Reduce cost" action |
| Offline | Read-only cached itinerary with an "Offline" chip |
| Empty trips list | Illustration + "Plan your first trip" |

## 6. Real-Time Behavior (frontend contract)

- Plan generation, replans, and chat stream over **SSE** (see `05_API_AND_AGENT_CONTRACT.md`).
- Frontend renders events by `type` and updates the timeline incrementally.
- Disruption alerts arrive as an SSE/poll update on the trip (`GET /trips/{id}/proposals?status=pending`).

## 7. Component List (for frontend dev)

`TripCard`, `TripWizard`, `DayNav`, `ItineraryItemCard`, `TravelConnector`, `DaySummary`, `DisruptionBanner`, `ProposalSheet`, `DiffView`, `AgentTimeline`, `AgentChat`, `BudgetBar`, `ExpenseForm`, `MapView`, `VersionList`, `SimulateMenu`.

## 8. Accessibility

- WCAG AA contrast; never rely on colour alone (icons + text for diff add/remove).
- Keyboard navigable, ARIA labels on icon buttons, `aria-live` region for the agent timeline.
- Respect `prefers-reduced-motion`.

## 9. Microcopy Samples

- Banner: "Rain is likely on Day 2 afternoon. I found a swap that keeps your budget."
- Approve toast: "Done. Itinerary updated to v3."
- Reject toast: "No changes made. I'll keep watching."
- Error: "Couldn't reach the weather service. Using the last forecast from 2 hours ago."
