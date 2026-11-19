'use client';

import React from 'react';
import { BudgetSummary } from '@/types/contract';
import { formatCurrency } from '@/lib/format';
import { AlertTriangle, Wallet } from 'lucide-react';

interface BudgetBarProps {
  budget: BudgetSummary;
  currency?: string;
  onReduceCost?: () => void;
  className?: string;
}

export function BudgetBar({
  budget,
  currency = 'INR',
  onReduceCost,
  className = '',
}: BudgetBarProps) {
  const { planned_total, actual_total, overrun_pct } = budget;
  const pctUsed = planned_total > 0 ? (actual_total / planned_total) * 100 : actual_total > 0 ? 100 : 0;
  const isOver100 = pctUsed > 100;
  const isPast90 = pctUsed >= 90 && !isOver100;
  const isWarning = overrun_pct >= 10;
  const clampedPct = Math.max(0, Math.min(100, pctUsed));

  return (
    <div
      className={`card-surface p-4 sm:p-5 space-y-3 transition-all ${
        isWarning
          ? 'border-accent-border bg-accent-bg/40'
          : ''
      } ${className}`}
    >
      <div className="flex items-center justify-between text-caption font-semibold">
        <span className="flex items-center gap-1.5 uppercase tracking-wider text-text-muted">
          <Wallet size={16} strokeWidth={1.75} className="text-primary" />
          Budget Tracker
        </span>
        <span
          className={`tabular-mono text-small font-bold ${
            isWarning ? 'text-accent' : isOver100 ? 'text-danger' : 'text-text-primary'
          }`}
        >
          {formatCurrency(actual_total, currency)} / {formatCurrency(planned_total, currency)}
        </span>
      </div>

      {/* Progress Bar: neutral fill under 90%, amber at 90%, red (--danger) over 100% */}
      <div className="w-full bg-[var(--surface-alt)] border border-border/40 h-2.5 rounded-pill overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            isOver100
              ? 'bg-danger'
              : isPast90 || isWarning
              ? 'bg-accent'
              : 'bg-gradient-to-r from-primary to-[var(--primary-gradient-to)]'
          }`}
          style={{ width: `${clampedPct}%` }}
          role="progressbar"
          aria-label="Trip budget progress"
          aria-valuenow={Math.round(clampedPct)}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      {/* Warning Alert if >= 10% overrun */}
      {isWarning && (
        <div className="pt-1 flex items-center justify-between gap-2 text-caption text-accent font-semibold">
          <div className="flex items-center gap-1.5">
            <AlertTriangle size={16} strokeWidth={1.75} className="shrink-0 text-accent" />
            <span>Overrun by {Math.round(overrun_pct)}%</span>
          </div>
          {onReduceCost && (
            <button
              type="button"
              onClick={onReduceCost}
              className="text-caption font-bold underline hover:text-amber-900 dark:hover:text-amber-200 transition-colors"
            >
              Reduce cost
            </button>
          )}
        </div>
      )}
    </div>
  );
}
