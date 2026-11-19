import React from 'react';
import { LucideIcon, ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface StatTileProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  delta?: {
    value: string | number;
    direction: 'up' | 'down' | 'neutral';
    isPositive?: boolean; // e.g. cost reduction is positive
  };
  subtext?: string;
  className?: string;
}

export function StatTile({
  label,
  value,
  icon: Icon,
  delta,
  subtext,
  className = '',
}: StatTileProps) {
  return (
    <div
      className={`card-surface p-4 flex flex-col justify-between ${className}`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-caption uppercase tracking-wider text-text-secondary font-medium">
          {label}
        </span>
        {Icon && (
          <Icon size={16} strokeWidth={1.75} className="text-text-muted" aria-hidden="true" />
        )}
      </div>

      <div className="flex items-baseline justify-between gap-2">
        <span className="tabular-mono text-xl sm:text-2xl font-bold text-text-primary">
          {value}
        </span>

        {delta && (
          <div
            className={`flex items-center text-xs font-semibold tabular-mono ${
              delta.isPositive
                ? 'text-success dark:text-success-text'
                : delta.isPositive === false
                ? 'text-danger dark:text-danger-text'
                : 'text-text-muted'
            }`}
          >
            {delta.direction === 'up' && (
              <ArrowUpRight size={16} strokeWidth={1.75} className="mr-0.5" aria-hidden="true" />
            )}
            {delta.direction === 'down' && (
              <ArrowDownRight size={16} strokeWidth={1.75} className="mr-0.5" aria-hidden="true" />
            )}
            <span>{delta.value}</span>
          </div>
        )}
      </div>

      {subtext && (
        <span className="text-[11px] text-text-muted mt-1">
          {subtext}
        </span>
      )}
    </div>
  );
}
