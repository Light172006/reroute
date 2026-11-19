'use client';

import React, { useState, useMemo } from 'react';
import { ItineraryVersion, ItineraryDay, ProposalDiffItem } from '@/types/contract';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { formatCurrency, formatRelativeTime } from '@/lib/format';
import { computeVersionDiff } from '@/lib/diff';
import { DiffView } from './DiffView';
import { IconCircle } from '@/components/primitives/IconCircle';
import {
  History,
  RotateCcw,
  GitCompare,
  Clock,
  User,
  Bot,
  CheckCircle2,
  Calendar,
} from 'lucide-react';

interface VersionListProps {
  versions: ItineraryVersion[];
  currentVersionId?: string | null;
  onRestore: (versionId: string) => void;
  isRestoring?: boolean;
  currency?: string;
  allVersionDays?: Record<string, ItineraryDay[]>;
  className?: string;
}

export function VersionList({
  versions,
  currentVersionId,
  onRestore,
  isRestoring = false,
  currency = 'INR',
  allVersionDays = {},
  className = '',
}: VersionListProps) {
  const [selectedV1, setSelectedV1] = useState<string | null>(
    versions.length > 1 ? versions[versions.length - 2]?.id : null
  );
  const [selectedV2, setSelectedV2] = useState<string | null>(
    versions.length > 0 ? versions[versions.length - 1]?.id : null
  );
  const [isComparing, setIsComparing] = useState(false);

  const sorted = useMemo(() => {
    return [...versions].sort((a, b) => b.version_no - a.version_no);
  }, [versions]);

  const computedDiff = useMemo(() => {
    if (!selectedV1 || !selectedV2 || !allVersionDays[selectedV1] || !allVersionDays[selectedV2]) {
      return [];
    }
    const diffRows = computeVersionDiff(allVersionDays[selectedV1], allVersionDays[selectedV2]);
    return diffRows
      .filter((r) => r.op !== 'unchanged')
      .map(
        (r): ProposalDiffItem => ({
          op: r.op as ProposalDiffItem['op'],
          day: r.day,
          stable_key: r.key,
          before: r.before,
          after: r.after,
          why: r.why,
        })
      );
  }, [selectedV1, selectedV2, allVersionDays]);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <History className="h-5 w-5 text-primary" strokeWidth={1.75} />
            Version History
          </h2>
          <p className="text-xs sm:text-sm text-text-secondary mt-0.5">
            Every approved replan or manual edit creates an immutable, restorable snapshot.
          </p>
        </div>

        {versions.length > 1 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsComparing(!isComparing)}
            className="gap-2 text-xs font-semibold"
          >
            <GitCompare className="h-4 w-4" strokeWidth={1.75} />
            {isComparing ? 'Hide Comparison' : 'Compare Two Versions'}
          </Button>
        )}
      </div>

      {/* Comparison Selector */}
      {isComparing && (
        <Card className="p-5 bg-surface-alt border-border space-y-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-secondary">
            <GitCompare className="h-4 w-4 text-primary" strokeWidth={1.75} />
            Select Versions to Compare
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label htmlFor="compare-base-version" className="block font-medium text-text-secondary mb-1.5">
                Base Version (From)
              </label>
              <select
                id="compare-base-version"
                aria-label="Base Version (From)"
                value={selectedV1 || ''}
                onChange={(e) => setSelectedV1(e.target.value)}
                className="w-full h-10 rounded-input border border-border bg-surface px-3 font-mono text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {sorted.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version_no} — {v.reason}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="compare-target-version" className="block font-medium text-text-secondary mb-1.5">
                Target Version (To)
              </label>
              <select
                id="compare-target-version"
                aria-label="Target Version (To)"
                value={selectedV2 || ''}
                onChange={(e) => setSelectedV2(e.target.value)}
                className="w-full h-10 rounded-input border border-border bg-surface px-3 font-mono text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {sorted.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version_no} — {v.reason}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="pt-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-3">
              Diff View
            </div>
            {computedDiff.length === 0 ? (
              <div className="p-6 text-center text-xs text-text-muted border border-dashed rounded-card">
                No differences found between these two versions.
              </div>
            ) : (
              <DiffView diff={computedDiff} currency={currency} />
            )}
          </div>
        </Card>
      )}

      {/* Vertical Timeline */}
      <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-border">
        {sorted.map((version) => {
          const isCurrent = version.id === currentVersionId;
          const isAgent = version.created_by.startsWith('agent:');

          return (
            <div key={version.id} className="relative group">
              {/* Timeline Node Icon */}
              <div className="absolute -left-6 sm:-left-8 top-3 -translate-x-1/2 z-10">
                <IconCircle
                  size="sm"
                  color={isCurrent ? 'blue' : isAgent ? 'indigo' : 'slate'}
                  className={isCurrent ? 'ring-4 ring-primary/20' : ''}
                >
                  {isAgent ? (
                    <Bot className="h-4 w-4" strokeWidth={1.75} />
                  ) : (
                    <User className="h-4 w-4" strokeWidth={1.75} />
                  )}
                </IconCircle>
              </div>

              {/* Version Card */}
              <Card
                className={`p-5 transition-all duration-150 ${
                  isCurrent
                    ? 'border-primary ring-1 ring-primary/40 bg-primary/5'
                    : 'hover:border-border hover:-translate-y-0.5'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    {/* Meta row */}
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono font-bold text-sm text-primary px-2 py-0.5 rounded bg-primary/10">
                        v{version.version_no}
                      </span>

                      {isAgent ? (
                        <Badge variant="secondary" className="gap-1.5 text-xs">
                          <Bot className="h-3.5 w-3.5 text-indigo-500" strokeWidth={1.75} />
                          Agent Replan
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="gap-1.5 text-xs">
                          <User className="h-3.5 w-3.5 text-text-secondary" strokeWidth={1.75} />
                          User Edit
                        </Badge>
                      )}

                      {isCurrent && (
                        <Badge variant="default" className="gap-1 text-xs font-semibold">
                          <CheckCircle2 className="h-3.5 w-3.5" strokeWidth={1.75} />
                          Current Active
                        </Badge>
                      )}

                      <span className="text-xs text-text-muted font-mono ml-auto sm:ml-0 flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5" strokeWidth={1.75} />
                        {formatRelativeTime(version.created_at)}
                      </span>
                    </div>

                    {/* Reason */}
                    <h3 className="font-semibold text-base text-text-primary">
                      {version.reason}
                    </h3>

                    {/* Summary */}
                    {version.summary && (
                      <p className="text-xs sm:text-sm text-text-secondary">
                        {version.summary}
                      </p>
                    )}

                    {/* Cost & Date info */}
                    <div className="flex items-center gap-3 pt-1 text-xs text-text-muted">
                      <span className="font-mono font-medium">
                        Budget total: {formatCurrency(version.total_cost, currency)}
                      </span>
                      <span>•</span>
                      <span>{new Date(version.created_at).toLocaleString()}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  {!isCurrent && (
                    <div className="shrink-0 flex items-center sm:self-center">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onRestore(version.id)}
                        disabled={isRestoring}
                        className="gap-2 text-xs font-semibold hover:border-primary hover:text-primary transition-colors"
                      >
                        <RotateCcw className="h-4 w-4" strokeWidth={1.75} />
                        Restore this version
                      </Button>
                    </div>
                  )}
                </div>
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
}
