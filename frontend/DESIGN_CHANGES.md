# Reroute UI/UX Design System Upgrades

This document details the visual, typographic, motion, and interaction design overhaul performed on Reroute. Reroute transitioned from an unstyled, functional skeleton into a polished, modern, calm, and confidence-inspiring travel companion that users would be proud to use and screenshot.

---

## 1. Design Principles & Hard Boundaries Observed

1. **Zero Emojis Everywhere**:
   - Zero unicode emojis exist in UI, mock data, tests, toast notifications, badges, or empty states.
   - Enforced by an automated Vitest suite in [src/no-emoji.test.ts](file:///d:/reroute/src/no-emoji.test.ts).
   - Replaced exclusively with uniform SVG vector icons from `lucide-react`.

2. **Consistent Iconography**:
   - Every icon in the application uses `strokeWidth={1.75}` and strictly one of three optical scales: **16px**, **20px**, or **24px**.
   - All icons inherit `currentColor` dynamically from their container tokens.
   - All icon-only buttons include descriptive `aria-label` tags for screen readers.

3. **Color Palette & Light/Dark Theming**:
   - **Primary**: Blue anchor `#2563EB` transitioning to `#4F46E5` via a soft gradient (`btn-primary-gradient`) for buttons, active states, and hero accents.
   - **Accent (Disruptions & Attention)**: Amber `#F59E0B`, paired with a gentle warm tint `#FFFBEB` (dark: `#2A2108`).
   - **Success & Danger**: Emerald `#16A34A` and Crimson `#DC2626` paired with 50-tint backgrounds and subtle borders.
   - **Neutrals**: Slate scale. Light page background `#F8FAFC`, cards `#FFFFFF`. Dark page `#0B1220`, cards `#111A2E`, borders `#1E293B`.
   - **Category Palette**: 8 soft tinted icon circles with matched glyph colors: Sightseeing (Blue), Food (Orange), Culture (Violet), Nature (Green), Nightlife (Indigo), Shopping (Pink), Adventure (Red), Transport (Slate).

4. **Surfaces, Glass Effects & Depth**:
   - Standard cards feature a 16px radius (`rounded-card`), 1px low-contrast borders, layered soft shadows (`0 1px 2px + 0 8px 24px` at low opacity), and a gentle 2px hover lift (`hover:-translate-y-0.5`).
   - **Glass Effect Strict Scope**: `backdrop-blur` and translucent surfaces are restricted to the sticky header, mobile bottom tab bar, and modal/sheet containers.

5. **Typography & Alignment**:
   - **Inter** for all UI copy with optimized tabular metrics and `letter-spacing: -0.02em` on Display/H1/H2 headings.
   - **JetBrains Mono** for all figures, times, costs, and durations (`tabular-nums`) ensuring column alignment across the itinerary and budget tabs.
   - Strict 4px spacing rhythm (4, 8, 12, 16, 20, 24, 32, 48, 64px). Left-aligned content paired with right-aligned tabular numbers.

---

## 2. Component & Screen-by-Screen Upgrades

### Sticky Header & Navbar
- Upgraded to a floating glass bar with a stylized `Route` brand wordmark, destination breadcrumbs, version indicator, primary "Check my plan now" refresh action, and ghost "Simulate disruption" dropdown with a `Zap` icon.
- In-place light/dark mode toggle button with smooth CSS transition.

### My Trips (`/trips`)
- Full-bleed destination cards with smooth dark gradient overlay, white typography, and reactive status chips.
- Animated pulsating amber dot on the "Needs attention" badge when a replan is pending.
- Warm empty state with decorative blurred background mesh and an `IconCircle` compass illustration.

### Trip Creation Wizard (`/trips/new`)
- Segmented progress bar with step labels and tinted circle step numbers.
- Step 1: Destination input with popular destination chips.
- Step 2: Custom budget slider with real-time value pill badge and currency switcher.
- Step 3: Selectable vibe pill chips with category icons and checkmarks; segmented pace control (Leaf = Relaxed, Scale = Balanced, Zap = Packed).

### Itinerary Items & Vertical Rail
- Fixed 64px left column in tabular mono for stop times.
- Vertical connector rail linking stops with dashed travel connectors showing mode icons and walking/transit durations.
- Category icon circles and badging (`Outdoor`, `Weather risk`, `Locked`).
- Locked items feature a prominent blue left border (`border-l-4 border-l-primary`), a lock icon badge, and disabled drag handle.

### Disruption Radar & Proposal Review Modal
- Warm amber disruption banner with an alert icon circle and high-contrast review button.
- Slide-down animation on arrival.
- Proposal Review modal features:
  - Data source pill (`Open-Meteo Weather API`).
  - Stat tiles row displaying cost delta (`-Rs 150` with green trend arrow), time delta (`+10m`), and items changed.
  - Side-by-side (desktop) and stacked (mobile) before/after `DiffView`: red strikethrough with a minus icon for removed stops; green highlight with a plus icon for proposed replacements. Locked items never appear in the diff.
  - Sticky footer with Approve, Reject, and Show Alternatives actions.

### Agent Panel & Timeline
- Stepper statuses for streamed LangGraph execution steps (spinning loader, checkmark, error cross).
- Monospace node names in caption caps with right-aligned execution latencies.
- Chat UI with primary user bubbles, tinted assistant bubbles, and clickable wand suggestion chips.

### Budget & Analytics Tab
- Clean custom SVG donut chart displaying category spend distribution with center total summary.
- Overrun alert banner triggered whenever spend exceeds planned budget by ≥ 10%.
- Interactive expense logging form and breakdown list with category icon circles and right-aligned tabular mono amounts.

### Map Tab
- Custom Leaflet map with CARTO light/dark tiles matching the active theme.
- Numbered SVG marker pins in primary blue; affected disruption stops highlighted in amber.
- Clicking pins opens an interactive stop card with category icons and details.

### Version History (`/trips/[id]/versions`)
- Vertical snapshot timeline with author badges (`Bot` vs `User`) and relative time stamps (`Just now`, `2h ago`).
- Interactive version comparison tool with real-time `DiffView`.
- Restore button with an undo icon (`RotateCcw`).

### Design System & Styleguide (`/dev/styleguide`)
- A living catalog showcasing color swatches, typography scales, lucide icon instances, button variants, status chips, card types, diff rows, and timeline states with an interactive theme switcher.

---

## 3. Verification & Test Suite

1. **Unit Tests**:
   - `npm test`: Ran 5 test files (12 tests total), all passing.
   - Includes `src/no-emoji.test.ts` scanning all source files in `src/` to strictly enforce zero emoji usage.

2. **End-to-End User Flows**:
   - `npm run test:e2e`:
     - **Flow 1**: Create trip wizard -> generate -> view itinerary in workspace.
     - **Flow 2**: Simulate rain disruption -> review proposal sheet -> approve changes -> new version v2 created.
     - **Visual Capture**: Full screenshot capture suite executing against all 7 key views in light and dark mode.

3. **Visual Screenshots Generated**:
   Saved in `screenshots/`:
   - `01-landing-light.png` & `01-landing-dark.png`
   - `02-trips-list-light.png` & `02-trips-list-dark.png`
   - `03-workspace-banner-light.png` & `03-workspace-banner-dark.png`
   - `04-proposal-review-light.png` & `04-proposal-review-dark.png`
   - `05-map-tab-light.png` & `05-map-tab-dark.png`
   - `06-budget-tab-light.png` & `06-budget-tab-dark.png`
   - `07-styleguide-light.png` & `07-styleguide-dark.png`

4. **Production Build**:
   - `npm run build`: Compiled with zero TypeScript or ESLint errors across all static and dynamic routes.
