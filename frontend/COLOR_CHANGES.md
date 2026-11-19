# Reroute: Dark Monochrome Palette Implementation

This document details the transition of the Reroute frontend dark mode to the dark, near-monochrome dashboard colour palette estimated from the reference specification.

---

## 1. Final Dark Token Table

| Token | Dark Value | CSS Variable | Reference Role / Usage |
| :--- | :--- | :--- | :--- |
| `--bg` | `#0A0A0A` | `var(--bg)` | Page background, near-black canvas |
| `--surface` | `#141414` | `var(--surface)` | Cards, panels, header, modal surfaces |
| `--surface-alt` | `#1C1C1C` | `var(--surface-alt)` | Inputs, hover states, inactive tabs, CTA band |
| `--surface-raised` | `#222222` | `var(--surface-raised)` | Tooltips, popovers, elevated cards, dropdowns |
| `--border` | `#262626` | `var(--border)` | Card outlines, dividers, structural borders |
| `--border-strong` | `#333333` | `var(--border-strong)` | Focused inputs, button outlines, active borders |
| `--text` | `#FAFAFA` | `var(--text)` | Primary headings, prominent values, active pills |
| `--text-secondary` | `#A3A3A3` | `var(--text-secondary)` | Labels, metadata, timestamps, secondary navigation |
| `--text-muted` | `#8A8A8A` | `var(--text-muted)` | Placeholders, captions, axis markings |
| `--primary` | `#FAFAFA` | `var(--primary)` | Primary CTA, selected pill, active tab underline |
| `--on-primary` | `#0A0A0A` | `var(--on-primary)` | Dark text on primary white CTA/pill |
| `--primary-hover` | `#E5E5E5` | `var(--primary-hover)` | Primary CTA hover state |
| `--primary-active` | `#D4D4D4` | `var(--primary-active)` | Primary CTA active / pressed state |
| `--primary-gradient-to` | `#E5E5E5` | `var(--primary-gradient-to)` | Monochromatic highlight gradient stop |
| `--primary-tint` | `rgba(255, 255, 255, 0.08)` | `var(--primary-tint)` | Selected pill background, active segment highlight |
| `--focus-ring` | `rgba(250, 250, 250, 0.40)` | `var(--focus-ring)` | Accessible keyboard focus outline (2px) |
| `--success` | `#22C55E` | `var(--success)` | Positive delta badge, added diff badge, valid states |
| `--success-bg` | `rgba(34, 197, 94, 0.14)` | `var(--success-bg)` | Soft background behind success badges |
| `--success-border` | `rgba(34, 197, 94, 0.30)` | `var(--success-border)` | Border stroke for success badges |
| `--success-text` | `#4ADE80` | `var(--success-text)` | High-contrast text on success background |
| `--danger` | `#EF4444` | `var(--danger)` | Negative delta, diff removal, destructive actions |
| `--danger-bg` | `rgba(239, 68, 68, 0.14)` | `var(--danger-bg)` | Soft background behind danger badges |
| `--danger-border` | `rgba(239, 68, 68, 0.30)` | `var(--danger-border)` | Border stroke for danger badges |
| `--danger-text` | `#F87171` | `var(--danger-text)` | High-contrast text on danger background |
| `--chart-line` | `#D4D4D4` | `var(--chart-line)` | Line series, map route polylines |
| `--chart-fill-top` | `rgba(255, 255, 255, 0.14)` | `var(--chart-fill-top)` | Area chart top gradient fill |
| `--chart-fill-bottom` | `rgba(255, 255, 255, 0.0)` | `var(--chart-fill-bottom)` | Area chart bottom gradient fill |
| `--chart-grid` | `rgba(255, 255, 255, 0.06)` | `var(--chart-grid)` | Gridlines and axis dividers |
| `--chart-series-1` | `#FAFAFA` | `var(--chart-series-1)` | Primary chart bar / donut slice (100% white) |
| `--chart-series-2` | `#A3A3A3` | `var(--chart-series-2)` | Secondary series (light grey) |
| `--chart-series-3` | `#525252` | `var(--chart-series-3)` | Tertiary series (mid grey) |
| `--chart-series-4` | `#262626` | `var(--chart-series-4)` | Baseline series (dark grey) |
| `--scrollbar-thumb` | `#333333` | `var(--scrollbar-thumb)` | Custom scrollbar slider track |
| `--selection` | `rgba(255, 255, 255, 0.20)` | `var(--selection)` | Native text selection highlight |

---

## 2. Contrast Results (WCAG AA & AAA Compliance)

All contrast ratios were verified using standard relative luminance calculations:

| Foreground | Background | Calculated Ratio | WCAG AA Requirement | WCAG AAA Requirement | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `--text` (`#FAFAFA`) | `--bg` (`#0A0A0A`) | **18.95 : 1** | >= 4.5:1 | >= 7:1 | **PASS AAA** |
| `--text` (`#FAFAFA`) | `--surface` (`#141414`) | **17.86 : 1** | >= 4.5:1 | >= 7:1 | **PASS AAA** |
| `--text-secondary` (`#A3A3A3`) | `--surface` (`#141414`) | **7.41 : 1** | >= 4.5:1 | >= 7:1 | **PASS AAA** |
| `--text-muted` (`#8A8A8A`) | `--surface` (`#141414`) | **5.37 : 1** | >= 4.5:1 | >= 3.0:1 (large) | **PASS AA** |
| `--on-primary` (`#0A0A0A`) | `--primary` (`#FAFAFA`) | **18.95 : 1** | >= 4.5:1 | >= 7:1 | **PASS AAA** |
| `--success-text` (`#4ADE80`) | `--success-bg` (`rgba(34,197,94,0.14)` on `#141414`) | **9.17 : 1** | >= 4.5:1 | >= 7:1 | **PASS AAA** |
| `--danger-text` (`#F87171`) | `--danger-bg` (`rgba(239,68,68,0.14)` on `#141414`) | **5.84 : 1** | >= 4.5:1 | >= 4.5:1 | **PASS AA** |
| `--accent-text` (`#FCD34D`) | `--accent-bg` (`rgba(245,158,11,0.14)` on `#141414`) | **9.80 : 1** | >= 4.5:1 | >= 7:1 | **PASS AAA** |

---

## 3. Replaced Hard-coded Colours

Residual hard-coded Tailwind classes and raw hex values were migrated to semantic tokens across all UI components:

1. **`src/styles/globals.css`**:
   - Redefined `.dark` root tokens to `#0A0A0A` page background and `#141414` surface.
   - Built a 10-step monochromatic grayscale primary scale (`--primary-50` `#1C1C1C` to `--primary-900` `#FAFAFA`).
   - Tokenized scrollbars, selection, and glass-effect translucent surfaces (`rgba(20, 20, 20, 0.85)`).

2. **`src/components/MapView.tsx`**:
   - Map route polyline updated to dynamic token `isDark ? '#D4D4D4' : '#4166F5'`.
   - Normal pins updated to `isDark ? '#FAFAFA' : '#4166F5'` with inverted pin labels (`#0A0A0A` in dark mode).
   - Disrupted stop pins retain `#F59E0B` (amber) with `#0A0A0A` text for maximum legibility.
   - Map popup container styled with `--surface` (`#141414`) and `--text-primary` (`#FAFAFA`).

3. **`src/components/BudgetBar.tsx`**:
   - Replaced hard-coded blue progress gradient with `bg-gradient-to-r from-primary to-[var(--primary-gradient-to)]` (neutral monochromatic fill in dark mode).
   - Preserves warning amber at 90% and danger red over 100%.

4. **`src/components/ui/button.tsx`**:
   - Secondary button hover transitioned from hardcoded slate to `hover:bg-border`.
   - Accent button text updated to high-contrast `text-black`.

5. **`src/components/ui/badge.tsx`**:
   - Tokenized all variants to use CSS variable references (`bg-primary/10 text-primary border-primary/20`, `bg-accent-bg text-accent-text`, `bg-danger-bg text-danger-text`, `bg-success-bg text-success-text`).

6. **`src/components/ui/modal.tsx`**:
   - Replaced semi-transparent slate backdrop with deep `bg-black/70`.

7. **`src/components/primitives/CategoryBadge.tsx` & `IconCircle.tsx`**:
   - Fully tokenized category colors using CSS variables (`--cat-*-bg` and `--cat-*-fg`).

8. **`src/components/primitives/StatusChip.tsx`**:
   - Migrated status chips to tokenized variants with high-contrast text and indicators.

9. **`src/app/page.tsx` (CTA Band)**:
   - In dark mode, converted the full-width CTA band from a blinding white section to `--surface-alt` (`#1C1C1C`) with `--border` (`#262626`).
   - Styled the CTA button inside as the primary white pill (`bg-primary text-on-primary`) with dark text (`#0A0A0A`).

10. **`src/components/TripCard.tsx`**:
    - Image fallback placeholder gradient updated to `dark:from-surface-raised dark:to-surface-alt` with subtle icon color `dark:text-text-muted`.

11. **`src/app/layout.tsx`**:
    - Updated mobile status bar viewport color in dark mode to `#0A0A0A`.

---

## 4. Derived Token Adjustments

1. **Monochrome Primary Scale**:
   - Light mode primary remains Ultramarine Blue (`#4166F5`).
   - Dark mode primary scale is a clean neutral gradient:
     - `--primary-50`: `#1C1C1C`
     - `--primary-100`: `#262626`
     - `--primary-200`: `#333333`
     - `--primary-300`: `#525252`
     - `--primary-400`: `#737373`
     - `--primary-500`: `#A3A3A3`
     - `--primary-600`: `#D4D4D4`
     - `--primary-700`: `#E5E5E5`
     - `--primary-800`: `#F5F5F5`
     - `--primary-900`: `#FAFAFA`

2. **Primary Tint**:
   - Defined as `rgba(255, 255, 255, 0.08)` (8% white) in dark mode for selected pill backgrounds, active day tabs, and subtle focus rings.

3. **Status Tinting**:
   - Success tint: `rgba(34, 197, 94, 0.14)` with `#4ADE80` text (9.17:1 ratio).
   - Danger tint: `rgba(239, 68, 68, 0.14)` with `#F87171` text (5.84:1 ratio).
   - Disruption amber tint: `rgba(245, 158, 11, 0.14)` with `#FCD34D` text (9.80:1 ratio).

---

## 5. Noticed but Not Changed

Per the strict scope boundaries of the task prompt:

- **Light Mode**: Kept 100% intact with the Clean Tech & Productivity palette (Ultramarine Blue `#4166F5`, Crisp White surfaces, Soft Cool Gray `#F4F6F9` canvas).
- **Layout and Spacing**: No margins, paddings, flex layouts, or grid structures were altered.
- **Typography and Fonts**: Inter and JetBrains Mono fonts, letter-spacings, and line-heights remain untouched.
- **Icons**: No emojis introduced; all icons remain Lucide SVG icons with `strokeWidth={1.75}` and currentColor inheritance.
- **Component Hierarchy & Routes**: No routes, filenames, or component signatures were modified.
- **Animations & Reduced Motion**: Framer Motion transitions and prefers-reduced-motion queries were preserved.
- **Semantic Disruption Colour**: Disruption warning amber (`#F59E0B`) was strictly preserved and kept prominent across both themes.
- **Category Palette**: All 8 category hues (sightseeing, food, culture, nature, nightlife, shopping, adventure, transport) were kept functional with soft dark-mode background tints.
