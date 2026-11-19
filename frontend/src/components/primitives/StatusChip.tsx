import React from 'react';
import { TripStatus } from '@/types/contract';
import {
  AlertTriangle,
  CheckCircle2,
  Calendar,
  FileEdit,
  Clock,
} from 'lucide-react';

interface StatusChipProps {
  status: TripStatus;
  hasPendingProposal?: boolean;
  className?: string;
}

export function StatusChip({
  status,
  hasPendingProposal = false,
  className = '',
}: StatusChipProps) {
  if (hasPendingProposal || status === 'needs_attention') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold bg-accent-bg text-accent-text border border-accent-border shadow-xs ${className}`}
      >
        <span className="relative flex h-2 w-2">
          <span className="attention-pulse absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
        </span>
        <AlertTriangle size={16} strokeWidth={1.75} aria-hidden="true" />
        <span>Needs attention</span>
      </span>
    );
  }

  switch (status) {
    case 'active':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold bg-success-bg text-success-text border border-success-border ${className}`}
        >
          <span className="h-2 w-2 rounded-full bg-success" />
          <CheckCircle2 size={16} strokeWidth={1.75} aria-hidden="true" />
          <span>Active</span>
        </span>
      );

    case 'planned':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold bg-primary/10 text-primary border border-primary/20 ${className}`}
        >
          <span className="h-2 w-2 rounded-full bg-primary" />
          <Calendar size={16} strokeWidth={1.75} aria-hidden="true" />
          <span>Planned</span>
        </span>
      );

    case 'done':
    case 'completed':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold bg-surface-alt text-text-secondary border border-border ${className}`}
        >
          <span className="h-2 w-2 rounded-full bg-text-muted" />
          <CheckCircle2 size={16} strokeWidth={1.75} aria-hidden="true" />
          <span>Done</span>
        </span>
      );

    case 'generating':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold bg-primary/10 text-primary border border-primary/20 ${className}`}
        >
          <span className="h-2 w-2 rounded-full bg-primary animate-ping" />
          <Clock size={16} strokeWidth={1.75} aria-hidden="true" />
          <span>Generating</span>
        </span>
      );

    case 'draft':
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold bg-surface-alt text-text-muted border border-border ${className}`}
        >
          <span className="h-2 w-2 rounded-full bg-text-muted" />
          <FileEdit size={16} strokeWidth={1.75} aria-hidden="true" />
          <span>Draft</span>
        </span>
      );
  }
}
