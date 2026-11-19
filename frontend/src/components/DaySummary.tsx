import React from 'react';
import { DaySummaryData } from '@/types/contract';
import { formatCurrency, formatDuration } from '@/lib/format';
import { Wallet, Footprints, Clock } from 'lucide-react';

interface DaySummaryProps {
  summary: DaySummaryData;
  currency?: string;
  className?: string;
}

export function DaySummary({ summary, currency = 'INR', className = '' }: DaySummaryProps) {
  return (
    <footer
      aria-label="Day summary metrics"
      className={`card-surface p-4 sm:p-5 ${className}`}
    >
      <div className="text-caption uppercase tracking-wider text-text-muted font-semibold mb-3">
        Day Summary
      </div>
      <div className="grid grid-cols-3 gap-3 divide-x divide-border text-center">
        {/* Cost */}
        <div className="px-2">
          <div className="flex items-center justify-center gap-1.5 text-caption text-text-muted mb-1">
            <Wallet size={16} strokeWidth={1.75} className="text-primary shrink-0" aria-hidden="true" />
            <span>Est. Cost</span>
          </div>
          <div className="tabular-mono text-small sm:text-h3 font-bold text-text-primary">
            {formatCurrency(summary.cost, currency)}
          </div>
        </div>

        {/* Walking */}
        <div className="px-2">
          <div className="flex items-center justify-center gap-1.5 text-caption text-text-muted mb-1">
            <Footprints size={16} strokeWidth={1.75} className="text-success shrink-0" aria-hidden="true" />
            <span>Walking</span>
          </div>
          <div className="tabular-mono text-small sm:text-h3 font-bold text-text-primary">
            {formatDuration(summary.walking_min)}
          </div>
        </div>

        {/* Active Time */}
        <div className="px-2">
          <div className="flex items-center justify-center gap-1.5 text-caption text-text-muted mb-1">
            <Clock size={16} strokeWidth={1.75} className="text-accent shrink-0" aria-hidden="true" />
            <span>Active Time</span>
          </div>
          <div className="tabular-mono text-small sm:text-h3 font-bold text-text-primary">
            {formatDuration(summary.active_min)}
          </div>
        </div>
      </div>
    </footer>
  );
}
