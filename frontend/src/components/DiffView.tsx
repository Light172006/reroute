import React from 'react';
import { ProposalDiffItem } from '@/types/contract';
import { formatCurrency, formatTime } from '@/lib/format';
import { MinusCircle, PlusCircle, Lock, ArrowRight, CheckCircle2 } from 'lucide-react';

interface DiffViewProps {
  diff: ProposalDiffItem[];
  currency?: string;
  className?: string;
}

export function DiffView({ diff, currency = 'INR', className = '' }: DiffViewProps) {
  if (!diff || diff.length === 0) {
    return (
      <div className="card-surface p-6 text-center text-small text-text-muted">
        No differences between versions.
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`} aria-label="Itinerary change diff">
      {diff.map((item, idx) => {
        const isReplace = item.op === 'replace';
        const isRemove = item.op === 'remove';
        const isAdd = item.op === 'add';

        return (
          <div
            key={item.stable_key || idx}
            data-testid={`diff-item-${idx}`}
            className="card-surface p-4 sm:p-5 space-y-3"
          >
            {/* Header: Day and Why */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
              <span className="text-caption font-bold px-2.5 py-0.5 rounded-pill bg-surface-alt text-text-secondary">
                Day {item.day}
              </span>
              {item.why && (
                <span className="text-caption font-medium text-text-secondary italic">
                  &ldquo;{item.why}&rdquo;
                </span>
              )}
            </div>

            {/* Before / After Columns on desktop, stacked on mobile with arrow icon */}
            <div className="grid grid-cols-1 md:grid-cols-[1fr,auto,1fr] gap-3 items-center">
              {/* Before Column (Removed / Replaced) */}
              {item.before ? (
                <div
                  data-testid="diff-before"
                  className={`p-3.5 rounded-input border transition-all ${
                    isReplace || isRemove
                      ? 'border-danger-border bg-danger-bg text-danger-text'
                      : 'border-border text-text-muted'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-caption font-bold uppercase tracking-wider text-danger mb-1.5">
                    <MinusCircle size={16} strokeWidth={1.75} className="shrink-0" aria-hidden="true" />
                    <span>Removed stop</span>
                  </div>

                  <div className="font-medium text-small line-through decoration-danger/70">
                    {item.before.title}
                  </div>

                  <div className="tabular-mono text-caption mt-2 flex items-center justify-between text-danger-text">
                    <span>
                      {formatTime(item.before.start)} - {formatTime(item.before.end)}
                    </span>
                    <span>{formatCurrency(item.before.cost, currency)}</span>
                  </div>

                  {item.before.is_locked && (
                    <div className="mt-2 flex items-center gap-1 text-caption text-primary font-medium">
                      <Lock size={16} strokeWidth={1.75} aria-hidden="true" />
                      <span>Item is locked</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-3.5 rounded-input border border-dashed border-border text-caption text-text-muted flex items-center justify-center">
                  (No previous stop)
                </div>
              )}

              {/* Middle arrow indicator (desktop) */}
              <div className="hidden md:flex justify-center text-text-muted">
                <ArrowRight size={20} strokeWidth={1.75} />
              </div>

              {/* After Column (Added / Replacement) */}
              {item.after ? (
                <div
                  data-testid="diff-after"
                  className={`p-3.5 rounded-input border transition-all ${
                    isReplace || isAdd
                      ? 'border-success-border bg-success-bg text-success-text'
                      : 'border-border text-text-muted'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-caption font-bold uppercase tracking-wider text-success mb-1.5">
                    <PlusCircle size={16} strokeWidth={1.75} className="shrink-0" aria-hidden="true" />
                    <span>Proposed replacement</span>
                  </div>

                  <div className="font-semibold text-small">
                    {item.after.title}
                  </div>

                  <div className="tabular-mono text-caption mt-2 flex items-center justify-between text-success-text">
                    <span>
                      {formatTime(item.after.start)} - {formatTime(item.after.end)}
                    </span>
                    <span>{formatCurrency(item.after.cost, currency)}</span>
                  </div>

                  {item.after.setting && (
                    <div className="mt-2 text-caption font-medium">
                      Setting: <span className="capitalize">{item.after.setting}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-3.5 rounded-input border border-dashed border-border text-caption text-text-muted flex items-center justify-center">
                  (No replacement stop)
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
