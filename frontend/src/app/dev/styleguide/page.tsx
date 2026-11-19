'use client';

import React from 'react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { IconCircle, IconCircleVariant } from '@/components/primitives/IconCircle';
import { StatusChip } from '@/components/primitives/StatusChip';
import { CategoryBadge } from '@/components/primitives/CategoryBadge';
import { StatTile } from '@/components/primitives/StatTile';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import {
  Sun,
  Moon,
  Compass,
  Utensils,
  Landmark,
  Trees,
  PartyPopper,
  ShoppingBag,
  Sparkles,
  Bus,
  CheckCircle,
  AlertTriangle,
  RotateCcw,
  Zap,
  Lock,
  Plus,
  Minus,
  Clock,
  DollarSign,
  CloudRain,
  Eye,
  RefreshCw,
  History,
  Bot,
  User,
  Wrench,
  Trash2,
  Check,
} from 'lucide-react';

export default function StyleguidePage() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full flex-1 space-y-12">
      {/* Page Header & Theme Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text-primary">
            Reroute Design System & Styleguide
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Living component library, tokens, typography scale, and states in light and dark mode.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-surface-alt p-1.5 rounded-card border border-border">
          <Button
            variant={theme === 'light' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setTheme('light')}
            className="gap-2 text-xs font-semibold"
          >
            <Sun className="h-4 w-4" strokeWidth={1.75} /> Light
          </Button>
          <Button
            variant={theme === 'dark' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setTheme('dark')}
            className="gap-2 text-xs font-semibold"
          >
            <Moon className="h-4 w-4" strokeWidth={1.75} /> Dark
          </Button>
        </div>
      </div>

      {/* 1. COLOR PALETTE */}
      <section className="space-y-4">
        <SectionHeader
          title="Color System"
          description="Defined via CSS variables. Surfaces, primaries, semantic accents, and category tones."
        />

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 text-xs">
          {/* Primary */}
          <div className="rounded-card border border-border p-3 space-y-2 bg-surface">
            <div className="h-14 rounded-[8px] bg-primary flex items-center justify-center text-primary-foreground font-mono font-bold">
              #4166F5 / #FAFAFA
            </div>
            <div>
              <div className="font-semibold text-text-primary">Primary / CTA</div>
              <div className="text-text-muted font-mono text-[11px]">Ultramarine & White</div>
            </div>
          </div>

          {/* Gradient Partner */}
          <div className="rounded-card border border-border p-3 space-y-2 bg-surface">
            <div className="h-14 rounded-[8px] bg-[var(--primary-gradient-to)] flex items-center justify-center text-primary-foreground font-mono font-bold">
              #395AD8 / #E5E5E5
            </div>
            <div>
              <div className="font-semibold text-text-primary">Gradient Stop</div>
              <div className="text-text-muted font-mono text-[11px]">Subtle tint offset</div>
            </div>
          </div>

          {/* Accent Amber */}
          <div className="rounded-card border border-border p-3 space-y-2 bg-surface">
            <div className="h-14 rounded-[8px] bg-accent flex items-center justify-center text-slate-950 font-mono font-bold">
              #F59E0B
            </div>
            <div>
              <div className="font-semibold text-text-primary">Accent Amber</div>
              <div className="text-text-muted font-mono text-[11px]">Disruptions & attention</div>
            </div>
          </div>

          {/* Success */}
          <div className="rounded-card border border-border p-3 space-y-2 bg-surface">
            <div className="h-14 rounded-[8px] bg-success flex items-center justify-center text-white font-mono font-bold">
              #16A34A / #22C55E
            </div>
            <div>
              <div className="font-semibold text-text-primary">Success Green</div>
              <div className="text-text-muted font-mono text-[11px]">Diff additions & valid state</div>
            </div>
          </div>

          {/* Danger */}
          <div className="rounded-card border border-border p-3 space-y-2 bg-surface">
            <div className="h-14 rounded-[8px] bg-danger flex items-center justify-center text-white font-mono font-bold">
              #DC2626 / #EF4444
            </div>
            <div>
              <div className="font-semibold text-text-primary">Danger Red</div>
              <div className="text-text-muted font-mono text-[11px]">Diff removals & overruns</div>
            </div>
          </div>

          {/* Muted Neutral */}
          <div className="rounded-card border border-border p-3 space-y-2 bg-surface">
            <div className="h-14 rounded-[8px] bg-surface-alt border border-border flex items-center justify-center text-text-primary font-mono font-bold">
              #F4F6F9 / #1C1C1C
            </div>
            <div>
              <div className="font-semibold text-text-primary">Surface Alt</div>
              <div className="text-text-muted font-mono text-[11px]">Inputs & active items</div>
            </div>
          </div>
        </div>

        {/* Category Colors */}
        <div className="pt-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3">
            Category Palette (Icon circles & badges)
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
            {[
              { name: 'Sightseeing', color: 'blue', icon: Compass },
              { name: 'Food', color: 'orange', icon: Utensils },
              { name: 'Culture', color: 'violet', icon: Landmark },
              { name: 'Nature', color: 'green', icon: Trees },
              { name: 'Nightlife', color: 'indigo', icon: PartyPopper },
              { name: 'Shopping', color: 'pink', icon: ShoppingBag },
              { name: 'Adventure', color: 'red', icon: Sparkles },
              { name: 'Transport', color: 'slate', icon: Bus },
            ].map((cat) => {
              const Icon = cat.icon;
              return (
                <div
                  key={cat.name}
                  className="p-3 rounded-card border border-border bg-white dark:bg-card text-center space-y-2"
                >
                  <IconCircle size="md" variant={cat.color as IconCircleVariant} className="mx-auto">
                    <Icon className="h-5 w-5" strokeWidth={1.75} />
                  </IconCircle>
                  <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                    {cat.name}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 2. TYPOGRAPHY SCALE */}
      <section className="space-y-4">
        <SectionHeader
          title="Typography Scale"
          description="Inter for UI headings and body with strict letter-spacing; JetBrains Mono for costs, times, and tabular figures."
        />

        <Card className="p-6 space-y-6 shadow-card">
          <div className="space-y-1 border-b border-border pb-4">
            <span className="text-[11px] font-mono text-slate-400">Display 48px / Line-height 56px / Bold 700 / Tracking -0.02em</span>
            <div className="text-display font-bold text-slate-900 dark:text-slate-50">
              A trip plan that fixes itself.
            </div>
          </div>

          <div className="space-y-1 border-b border-border pb-4">
            <span className="text-[11px] font-mono text-slate-400">H1 30px / Line-height 38px / Bold 700</span>
            <h1 className="text-h1 font-bold text-slate-900 dark:text-slate-100">
              Trip Workspace & Itinerary
            </h1>
          </div>

          <div className="space-y-1 border-b border-border pb-4">
            <span className="text-[11px] font-mono text-slate-400">H2 24px / Line-height 32px / Semi-bold 650</span>
            <h2 className="text-h2 font-semibold text-slate-900 dark:text-slate-100">
              Day 2: Darjeeling Heritage Trail
            </h2>
          </div>

          <div className="space-y-1 border-b border-border pb-4">
            <span className="text-[11px] font-mono text-slate-400">H3 18px / Line-height 28px / Semi-bold 600</span>
            <h3 className="text-h3 font-semibold text-slate-900 dark:text-slate-100">
              Batasia Loop War Memorial & Toy Train
            </h3>
          </div>

          <div className="space-y-1 border-b border-border pb-4">
            <span className="text-[11px] font-mono text-slate-400">Body 15px / Line-height 24px / Regular 400</span>
            <p className="text-body text-slate-600 dark:text-slate-300">
              The agent continuously monitors live weather radars, municipal transit announcements, and venue opening hours.
            </p>
          </div>

          <div className="space-y-1 border-b border-border pb-4">
            <span className="text-[11px] font-mono text-slate-400">Small 13px / Line-height 20px / Medium 500</span>
            <p className="text-small text-slate-500 dark:text-slate-400">
              Estimated duration: 90 minutes • 1.2 km walking distance from previous stop.
            </p>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] font-mono text-slate-400">JetBrains Mono / Tabular Numbers</span>
            <div className="flex flex-wrap items-center gap-6 font-mono font-bold text-sm text-slate-900 dark:text-slate-100">
              <span>Rs 12,450 / Rs 15,000</span>
              <span className="text-success">+Rs 200</span>
              <span className="text-danger">-Rs 450</span>
              <span>09:30 - 11:00</span>
              <span>80% rain prob</span>
            </div>
          </div>
        </Card>
      </section>

      {/* 3. BUTTONS & CHIPS */}
      <section className="space-y-4">
        <SectionHeader
          title="Buttons & Controls"
          description="Fixed 40px/36px/48px heights, 8px/12px border-radius, scale 0.98 on press, no emojis."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-6 space-y-4 shadow-card">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Button Variants & Sizes
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button variant="primary">Primary Gradient</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="danger">Danger</Button>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Button size="sm" variant="primary">Small (36px)</Button>
              <Button size="default" variant="primary">Default (40px)</Button>
              <Button size="lg" variant="primary">Large (48px)</Button>
              <Button size="default" disabled variant="primary">Disabled</Button>
            </div>
          </Card>

          <Card className="p-6 space-y-4 shadow-card">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Status Chips & Badges
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <StatusChip status="draft" />
              <StatusChip status="planned" />
              <StatusChip status="needs_attention" />
              <StatusChip status="active" />
              <StatusChip status="done" />
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-2">
              <CategoryBadge category="sightseeing" />
              <CategoryBadge category="food" />
              <CategoryBadge category="culture" />
              <CategoryBadge category="nature" />
              <CategoryBadge category="nightlife" />
            </div>
          </Card>
        </div>
      </section>

      {/* 4. DISRUPTION BANNER & DIFF ROWS */}
      <section className="space-y-4">
        <SectionHeader
          title="Disruption Radar & Diff View"
          description="High-contrast banner with amber tint and side-by-side before/after replacement diffs."
        />

        {/* Disruption Banner Mock */}
        <div className="rounded-card border border-amber-300 dark:border-amber-700/80 bg-amber-50 dark:bg-amber-950/40 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-card">
          <div className="flex items-start sm:items-center gap-3">
            <IconCircle size="md" color="orange" className="shrink-0">
              <CloudRain className="h-5 w-5 text-accent" strokeWidth={1.75} />
            </IconCircle>
            <div>
              <div className="font-bold text-sm sm:text-base text-amber-900 dark:text-amber-200">
                Rain expected Day 2, 2-6pm (80%). 2 outdoor stops affected.
              </div>
              <div className="text-xs text-amber-800/80 dark:text-amber-300/80 mt-0.5">
                Targeted replacements keep your budget and locked stops completely intact.
              </div>
            </div>
          </div>
          <Button variant="primary" size="sm" className="shrink-0 font-semibold shadow-xs">
            Review changes
          </Button>
        </div>

        {/* Diff preview rows */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-card bg-red-50/60 dark:bg-red-950/30 border border-red-200 dark:border-red-900/60 space-y-2">
            <div className="flex items-center gap-2 font-bold text-danger text-xs">
              <Minus className="h-4 w-4" strokeWidth={1.75} />
              <span>Removed Stop</span>
            </div>
            <div className="line-through font-medium text-slate-800 dark:text-slate-200 text-sm">
              Happy Valley Tea Estate Tour
            </div>
            <div className="text-xs font-mono text-slate-400">14:00 - 16:00 • Rs 500</div>
          </div>

          <div className="p-4 rounded-card bg-green-50/60 dark:bg-green-950/30 border border-green-200 dark:border-green-900/60 space-y-2">
            <div className="flex items-center gap-2 font-bold text-success text-xs">
              <Plus className="h-4 w-4" strokeWidth={1.75} />
              <span>Added Replacement</span>
            </div>
            <div className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
              Tibetan Refugee Self-Help Center (Indoor)
            </div>
            <div className="text-xs font-mono text-slate-400">14:00 - 16:00 • Rs 200</div>
          </div>
        </div>
      </section>

      {/* 5. STAT TILES & TIMELINE STEPPERS */}
      <section className="space-y-4">
        <SectionHeader
          title="Stat Tiles & Stepper States"
          description="Glanceable metric tiles and aria-live polite agent timeline states."
        />

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatTile
            label="Total Cost Delta"
            value="-Rs 150"
            subtext="Within daily cap"
            delta={{ value: 'Rs 150 saved', direction: 'down', isPositive: true }}
          />
          <StatTile
            label="Time Difference"
            value="+15 min"
            subtext="Comfortable transit"
            delta={{ value: '15m transit', direction: 'up', isPositive: true }}
          />
          <StatTile
            label="Items Changed"
            value="2 stops"
            subtext="0 locked items touched"
          />
        </div>

        {/* Stepper items */}
        <Card className="p-5 space-y-3 shadow-card">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
            Agent Timeline Node States
          </div>

          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-xs p-2 rounded-[8px] bg-slate-50 dark:bg-slate-900">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-success" strokeWidth={1.75} />
                <span className="font-mono font-semibold">weather_checker</span>
                <span className="text-slate-500">Signal: Precipitation 80% confirmed</span>
              </div>
              <span className="font-mono text-slate-400 text-[11px]">120ms</span>
            </div>

            <div className="flex items-center justify-between text-xs p-2 rounded-[8px] bg-slate-50 dark:bg-slate-900">
              <div className="flex items-center gap-2">
                <Wrench className="h-4 w-4 text-primary" strokeWidth={1.75} />
                <span className="font-mono font-semibold">candidate_swap_tool</span>
                <span className="text-slate-500">Found 3 indoor cultural candidates</span>
              </div>
              <span className="font-mono text-slate-400 text-[11px]">340ms</span>
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
}
