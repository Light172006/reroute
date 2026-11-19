'use client';

import React from 'react';
import { BudgetSummary } from '@/types/contract';
import { formatCurrency } from '@/lib/format';
import { IconCircle } from '@/components/primitives/IconCircle';
import {
  Compass,
  Utensils,
  Landmark,
  Trees,
  PartyPopper,
  ShoppingBag,
  Sparkles,
  Bus,
  LucideIcon,
} from 'lucide-react';
import { IconCircleVariant } from './primitives/IconCircle';

const CATEGORY_CONFIG: Record<
  string,
  { color: string; bg: string; iconColor: IconCircleVariant; icon: LucideIcon }
> = {
  sightseeing: { color: 'var(--cat-sightseeing-fg)', bg: 'blue', iconColor: 'sightseeing', icon: Compass },
  food: { color: 'var(--cat-food-fg)', bg: 'orange', iconColor: 'food', icon: Utensils },
  culture: { color: 'var(--cat-culture-fg)', bg: 'violet', iconColor: 'culture', icon: Landmark },
  nature: { color: 'var(--cat-nature-fg)', bg: 'green', iconColor: 'nature', icon: Trees },
  nightlife: { color: 'var(--cat-nightlife-fg)', bg: 'indigo', iconColor: 'nightlife', icon: PartyPopper },
  shopping: { color: 'var(--cat-shopping-fg)', bg: 'pink', iconColor: 'shopping', icon: ShoppingBag },
  adventure: { color: 'var(--cat-adventure-fg)', bg: 'red', iconColor: 'adventure', icon: Sparkles },
  transport: { color: 'var(--cat-transport-fg)', bg: 'slate', iconColor: 'transport', icon: Bus },
};

interface BudgetDonutChartProps {
  budget: BudgetSummary;
  currency?: string;
  className?: string;
}

export function BudgetDonutChart({
  budget,
  currency = 'INR',
  className = '',
}: BudgetDonutChartProps) {
  const { by_category, actual_total, planned_total } = budget;

  // Filter categories that have actual spend, fallback to planned if no spend yet
  const activeSpendCategories = by_category.filter((c) => c.actual > 0);
  const categoriesToDraw =
    activeSpendCategories.length > 0
      ? activeSpendCategories
      : by_category.filter((c) => c.planned > 0);

  const totalToDraw = categoriesToDraw.reduce(
    (sum, c) => sum + (activeSpendCategories.length > 0 ? c.actual : c.planned),
    0
  );

  // SVG circle geometry
  const radius = 54;
  const strokeWidth = 16;
  const circumference = 2 * Math.PI * radius;

  let accumulatedPercent = 0;

  const segments = categoriesToDraw.map((cat) => {
    const val = activeSpendCategories.length > 0 ? cat.actual : cat.planned;
    const percent = totalToDraw > 0 ? val / totalToDraw : 0;
    const strokeDasharray = `${percent * circumference} ${circumference}`;
    const strokeDashoffset = -accumulatedPercent * circumference;
    accumulatedPercent += percent;

    const conf = CATEGORY_CONFIG[cat.category.toLowerCase()] || {
      color: 'var(--cat-transport-fg)',
      bg: 'slate',
      iconColor: 'transport' as IconCircleVariant,
      icon: Compass,
    };

    return {
      category: cat.category,
      value: val,
      percent,
      color: conf.color,
      strokeDasharray,
      strokeDashoffset,
    };
  });

  const spentPct = planned_total > 0 ? Math.round((actual_total / planned_total) * 100) : 0;

  return (
    <div className={`grid grid-cols-1 md:grid-cols-12 gap-6 items-center ${className}`}>
      {/* SVG Donut */}
      <div className="md:col-span-5 flex flex-col items-center justify-center relative">
        <div className="relative w-48 h-48 flex items-center justify-center">
          <svg
            viewBox="0 0 140 140"
            className="w-full h-full -rotate-90 transform"
            aria-label="Category spend donut chart"
            role="img"
          >
            {/* Background ring */}
            <circle
              cx="70"
              cy="70"
              r={radius}
              className="text-border"
              stroke="currentColor"
              strokeWidth={strokeWidth}
              fill="transparent"
            />

            {/* Segments */}
            {segments.map((seg) => (
              <circle
                key={seg.category}
                cx="70"
                cy="70"
                r={radius}
                stroke={seg.color}
                strokeWidth={strokeWidth}
                strokeDasharray={seg.strokeDasharray}
                strokeDashoffset={seg.strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
                className="transition-all duration-300"
              />
            ))}
          </svg>

          {/* Center text overlay */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
              {activeSpendCategories.length > 0 ? 'Spent' : 'Planned'}
            </span>
            <span className="text-base font-bold font-mono text-text-primary tracking-tight">
              {formatCurrency(actual_total, currency)}
            </span>
            <span className="text-[10px] font-mono text-text-secondary">
              {spentPct}% of cap
            </span>
          </div>
        </div>
      </div>

      {/* Category breakdown list */}
      <div className="md:col-span-7 space-y-2.5">
        <div className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
          Category Distribution
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {by_category.map((cat) => {
            const conf = CATEGORY_CONFIG[cat.category.toLowerCase()] || {
              color: 'var(--cat-transport-fg)',
              bg: 'slate',
              iconColor: 'transport' as IconCircleVariant,
              icon: Compass,
            };
            const Icon = conf.icon;
            const pct =
              planned_total > 0
                ? Math.round(((cat.actual || cat.planned) / planned_total) * 100)
                : 0;

            return (
              <div
                key={cat.category}
                className="flex items-center justify-between p-2.5 rounded-[10px] bg-surface-alt border border-border text-xs"
              >
                <div className="flex items-center gap-2">
                  <IconCircle size="sm" color={conf.iconColor}>
                    <Icon className="h-4 w-4" strokeWidth={1.75} />
                  </IconCircle>
                  <span className="font-medium capitalize text-text-primary">
                    {cat.category}
                  </span>
                </div>

                <div className="text-right">
                  <div className="font-mono font-semibold text-text-primary">
                    {formatCurrency(cat.actual > 0 ? cat.actual : cat.planned, currency)}
                  </div>
                  <div className="text-[10px] font-mono text-text-muted">{pct}% total</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
