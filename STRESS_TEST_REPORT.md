# Reroute Frontend Stress Test & Hardening Report

Date: 2026-11-19
Branch: `chore/frontend-folder-and-stress-tests`
Test Environment: MSW Mock Service Worker (`NEXT_PUBLIC_USE_MOCKS=true`)
Node.js & Next.js: Next.js 14.2.23 (App Router), TypeScript (strict mode)

---

## Executive Summary

A comprehensive QA and resilience audit was conducted across the Reroute frontend against the backend contract (`05_API_AND_AGENT_CONTRACT.md`) and design specifications (`02_UX_DESIGN.md`). All tests, builds, and linting were performed against the MSW mock layer without requiring a live backend.

Every issue discovered was resolved at the root cause. Zero tests were skipped, weakened, or suppressed with `eslint-disable` or `@ts-ignore`. Zero emojis are present anywhere in the codebase, tests, or documentation.

All automated verification gates are passing:
- TypeScript (`npx tsc --noEmit`): 0 errors
- ESLint (`npm run lint`): 0 warnings, 0 errors
- Vitest Unit & Stress Suite (`npm test`): 9 test files, 41 tests passing (100%)
- Next.js Production Build (`npm run build`): Compiled and generated all static & dynamic routes successfully
- Playwright E2E & Stress Flows: 24 tests passing across Chromium, Firefox, WebKit, and Mobile Chrome (100%)
- Axe Accessibility Audit (`@axe-core/playwright`): 16 tests passing across all 8 routes in both Light and Dark themes with 0 serious or critical violations

---

## Detailed Audit & Stress Test Results

### A1. Baseline Health

- Clean install and builds verified against clean node_modules and .next directories.
- Strictly eliminated all `any` types across `src/` by creating and adopting strict domain types: `ItineraryItem`, `LucideIcon`, `DisruptionType`, `SettingType`, `ExpenseCategory`, `IconCircleVariant`, `AgentEvent`, etc.
- Intercepted console errors and React key/hydration warnings in `vitest.setup.ts` to ensure unhandled warnings fail tests immediately.
- Zero emojis verified by automated test `src/no-emoji.test.ts` scanning all files in `src/`.
- Color tokens aligned with CSS custom variables; hard-coded hexes restricted to theme token files.

### A2. SSE and Real-Time Stream Stress

The real-time streaming layer (`src/hooks/useRunStream.ts`, `src/mocks/handlers.ts`, `src/lib/sse.ts`) was subjected to heavy edge cases:
- Event Flood (2,000 events in 10 seconds): The hook was rewritten to cap displayed events at `MAX_EVENTS = 300` and coalesce status updates by node/message in-place, preventing unbounded DOM allocation and maintaining sub-100ms UI responsiveness.
- Out of Order & Duplicates: Events arriving out of order are re-sorted by sequence number (`seq`), and duplicates are deduplicated via sequence tracking and node/message checks.
- Disconnect & Resume: Connection dropping triggers reconnection passing `Last-Event-ID`; missed events are replayed from that sequence onwards.
- Repeated Drops & Exponential Backoff: When stream drops repeated 20+ times, connection attempts back off up to 5s, stopping at 5 retries with a non-blocking UI alert and actionable "Retry" button.
- Malformed & Oversized Payloads: Handlers safely ignore malformed JSON and null payloads without crashing.
- Token Streaming: Incremental token events concatenate cleanly in `streamingText` and display dynamically in `AgentChat.tsx`.
- Connection Leaks: Verified `activeConnectionsCount` decrements to 0 upon component unmount and hook teardown.

### A3. Proposals & State Machine Stress

- Double-Click Idempotency: Synchronous ref lock (`isSubmittingRef.current`) in `ProposalSheet.tsx` prevents duplicate mutation dispatches on rapid double-clicks.
- 409 Already Decided: If an approval or rejection is repeated, the UI surfaces a clear warning toast without entering an inconsistent state.
- Superseded Proposals: When an active proposal is superseded by a newer proposal, older proposals display an explicit "Superseded" banner, disabling action buttons.
- Locked Items Protection: Locked stops (`is_locked: true`) are immutable; the replanning diff and mock handler strictly preserve locked items.

### A4. Data & Edge Cases Stress

- Zero-Cost & High-Cost Budgets: Budget bars and progress calculations clamp safely to 0-100%, handling 0 planned totals and high actual expenses without NaN or layout breaks.
- Date Formatting: `formatDateRange` in `src/lib/format.ts` correctly handles single-day trips, leap years, and cross-year boundaries (e.g., Dec 28, 2026 to Jan 4, 2027) without UTC/local timezone shifts.
- Large Datasets: Validated rendering of trips with 200 items across days and 1,000+ character notes.
- Empty States: Trips with no items or no expenses render dedicated empty-state cards.

### A5. Accessibility Audit (Axe & WCAG 2 AA)

Automated testing using `@axe-core/playwright` on all application routes in both Light Mode ("Clean Tech & Productivity") and Dark Mode ("Near-Monochrome High Contrast Dashboard"):
- Audited Routes: `/`, `/login`, `/signup`, `/trips`, `/trips/new`, `/trips/trip-darjeeling-01`, `/trips/trip-darjeeling-01/versions`, `/settings`.
- Light Mode Contrast: Adjusted light mode `--text-muted` from `#64748B` (4.39:1) to `#505E73` (5.98:1 on page background, 6.52:1 on cards), ensuring all muted labels, timestamps, and captions exceed the 4.5:1 WCAG AA threshold.
- ARIA Progressbar Name: Added `aria-label="Trip budget progress"` to the `BudgetBar` progressbar element.
- ARIA Prohibited Attributes: Replaced prohibited `aria-label` on non-role `span` in `ItineraryItemCard.tsx` with `role="img" aria-label="Item is locked"` and `aria-hidden="true"` on the lock icon.
- Landing Page Contrast: Removed text-dimming `opacity-60` on preview cards, replacing it with dashed borders; increased contrast of status badges in the preview diff banner (`text-red-700 dark:text-red-300` and `text-green-700 dark:text-green-300`).
- Result: 0 critical and 0 serious accessibility violations across all routes and modes.

### A6. Network Resilience & Offline Handling

- Handled network errors and simulated offline states with informative banner and toast alerts.
- Provided explicit manual retry actions for dropped SSE streams.
- Verified optimistic updates rollback on mutation failure.

### A7. Security Audit

- Map Popups: Applied strict HTML character escaping (`escapeHtml`) in Leaflet popup title interpolation in `src/components/MapView.tsx`, preventing script injection via malicious location names.
- Auth Tokens: Verified tokens are handled in memory and auth state without exposing sensitive keys in DOM attributes or console logs.

### A8. Cross-Browser & Multi-Viewport E2E Flows

Tested across 4 browser engine profiles in Playwright:
1. Chromium (Desktop)
2. Firefox (Desktop)
3. WebKit (Desktop Safari)
4. Mobile Chrome (Pixel 5 viewport)

Flows verified:
- Flow 1: Create trip wizard -> form validation -> generate itinerary -> view stops & budget.
- Flow 2: Simulate rain disruption -> review proposal sheet -> approve changes -> new itinerary version created.
- Flow 3: Reject proposal -> proposal dismissed with toast -> itinerary remains unaltered.
- Flow 4: Budget overrun -> add expense -> budget bar switches to overrun warning state.
- Flow 5: Assistant chat -> send prompt -> agent response and proposal generation.
- Flow 6: Keyboard accessibility -> navigate tabs and itinerary items using Tab, Enter, and arrow keys.

---

## Test Results & Metrics Summary

| Test Category | Suite / Tool | Tests Run | Result | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Static Type Analysis | TypeScript 5.6 | Whole codebase | Pass (0 errors) | Strict mode, zero `any` |
| Code Quality & Linter | ESLint + Next.js | Whole codebase | Pass (0 errors) | Zero rule disables |
| Emoji Audit | Vitest | 1 test | Pass | Zero emoji codepoints |
| SSE Real-Time Stream | Vitest | 9 tests | Pass | Flood, resume, deduping, backoff |
| Proposals & State Machine | Vitest | 6 tests | Pass | Idempotency, 409, locked items |
| Data & Edge Cases | Vitest | 11 tests | Pass | Dates, budgets, 200 items, empty states |
| Security | Vitest | 3 tests | Pass | XSS sanitization, HTML escaping |
| Component Unit Tests | Vitest | 11 tests | Pass | BudgetBar, DiffView, ProposalSheet |
| Accessibility Audit | Playwright + Axe | 16 tests | Pass (0 violations) | All 8 routes in light & dark mode |
| Multi-Browser E2E Flows | Playwright | 24 tests | Pass | Chromium, Firefox, WebKit, Mobile Chrome |
| Production Build | Next.js 14.2.23 | 10 routes | Pass | Static & dynamic generation clean |

---

## Root Causes and Fixes Applied

1. **Light Mode Text Contrast Under 4.5:1**
   - *Root Cause*: `--text-muted` value `#64748B` against `#F4F6F9` had a contrast ratio of 4.39:1 (threshold is 4.5:1).
   - *Fix*: Updated `--text-muted` in `src/styles/globals.css` to `#505E73`, achieving a 5.98:1 contrast ratio against the page background and 6.52:1 against cards.

2. **Progressbar Missing Accessible Name**
   - *Root Cause*: The progress indicator in `BudgetBar.tsx` used `role="progressbar"` with min/max/value attributes but lacked an accessible name.
   - *Fix*: Added `aria-label="Trip budget progress"`.

3. **Prohibited ARIA Attribute on Span**
   - *Root Cause*: In `ItineraryItemCard.tsx`, `aria-label="Item is locked"` was placed on a plain `<span>` element without an explicit ARIA role.
   - *Fix*: Added `role="img"` to the span and `aria-hidden="true"` to the SVG child.

4. **Landing Page Preview Card Low Contrast**
   - *Root Cause*: The landing page preview used `opacity-60` on a replaced stop card, reducing text contrast to 2.32:1.
   - *Fix*: Replaced `opacity-60` with a dashed border (`border-dashed border-border-strong`), preserving high text contrast while visually indicating the superseded state. Increased contrast of status text to high-contrast tokens.

5. **SSE Stream Unbounded Memory & Duplicate Ordering**
   - *Root Cause*: In rapid stream bursts, state appended all incoming events naively, causing memory churn and potential duplicate nodes.
   - *Fix*: In `useRunStream.ts`, capped stream events at 300 items, coalesced updates by node/message in-place, and re-sorted sequences.

6. **Proposal Double-Submission Race Condition**
   - *Root Cause*: Rapid successive clicks on "Approve" dispatched two parallel mutation requests before state updated.
   - *Fix*: Added synchronous reference guard `isSubmittingRef.current` in `ProposalSheet.tsx`.

7. **XSS Vulnerability in Leaflet Map Popups**
   - *Root Cause*: Map item titles were interpolated directly into raw HTML popups.
   - *Fix*: Added HTML entity escaping function `escapeHtml()` in `MapView.tsx`.
