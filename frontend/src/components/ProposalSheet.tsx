'use client';

import React, { useState } from 'react';
import { ProposalResponse } from '@/types/contract';
import { Modal } from '@/components/ui/modal';
import { DiffView } from './DiffView';
import { Button } from '@/components/ui/button';
import { formatDeltaCurrency } from '@/lib/format';
import { useDecideProposal } from '@/hooks/useProposal';
import { useUIStore } from '@/hooks/useUIStore';
import {
  Check,
  X,
  Shuffle,
  TrendingDown,
  TrendingUp,
  Clock,
  Layers,
  Database,
  Globe,
  Loader2,
} from 'lucide-react';

interface ProposalSheetProps {
  isOpen: boolean;
  onClose: () => void;
  proposal: ProposalResponse;
  tripId: string;
  currency?: string;
  onOpenStream?: (runId: string) => void;
}

export function ProposalSheet({
  isOpen,
  onClose,
  proposal,
  tripId,
  currency = 'INR',
  onOpenStream,
}: ProposalSheetProps) {
  const { mutate: decideProposal, isPending } = useDecideProposal(tripId);
  const { setToast } = useUIStore();
  const [decisionNote, setDecisionNote] = useState('');
  const isSubmittingRef = React.useRef(false);

  const handleDecision = (decision: 'approve' | 'reject' | 'alternatives') => {
    if (isSubmittingRef.current || isPending || proposal.status === 'superseded') return;
    isSubmittingRef.current = true;
    decideProposal(
      {
        proposalId: proposal.id,
        decision,
        note: decisionNote || undefined,
      },
      {
        onSuccess: (data) => {
          isSubmittingRef.current = false;
          onClose();
          if (decision === 'approve') {
            const versionStr = data.version_id ? ` to v${data.version_id.split('-v').pop() || 'new'}` : '';
            setToast({
              type: 'success',
              text: `Done. Itinerary updated${versionStr}.`,
            });
          } else if (decision === 'reject') {
            setToast({
              type: 'info',
              text: "No changes made. I'll keep watching.",
            });
          } else if (decision === 'alternatives' && data.run_id && onOpenStream) {
            setToast({
              type: 'info',
              text: 'Finding alternative options...',
            });
            onOpenStream(data.run_id);
          }
        },
        onError: (err: unknown) => {
          isSubmittingRef.current = false;
          const message =
            err instanceof Error ? err.message : 'Failed to apply decision. Please try again.';
          setToast({
            type: 'error',
            text: message,
          });
        },
      }
    );
  };

  const dataSource =
    proposal.disruptions?.[0]?.source || 'Open-Meteo real-time telemetry';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Review Itinerary Changes"
      description="Reroute detected a disruption and formulated this proposal for your approval."
      isBottomSheetOnMobile={true}
    >
      <div className="space-y-6">
        {/* Header: Reason as H2, source chip with database / globe icon */}
        <div className="card-surface p-4 sm:p-5 space-y-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2.5">
            <h2 className="text-h2 font-bold text-text-primary tracking-tight">
              {proposal.reason}
            </h2>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-surface-alt text-text-secondary text-caption font-mono border border-border">
              <Database size={16} strokeWidth={1.75} className="text-text-muted" aria-hidden="true" />
              <span>{dataSource}</span>
            </span>
          </div>

          {proposal.explanation && (
            <p className="text-small text-text-secondary leading-relaxed">
              {proposal.explanation}
            </p>
          )}
        </div>

        {/* Impact row as three stat tiles */}
        <div className="grid grid-cols-3 gap-3">
          {/* Cost Delta */}
          <div className="card-surface p-3.5 text-center flex flex-col justify-between">
            <span className="text-caption uppercase tracking-wider text-text-muted flex items-center justify-center gap-1 font-semibold">
              {proposal.cost_delta <= 0 ? (
                <TrendingDown size={16} strokeWidth={1.75} className="text-success" />
              ) : (
                <TrendingUp size={16} strokeWidth={1.75} className="text-danger" />
              )}
              Cost Delta
            </span>
            <div
              className={`tabular-mono text-small sm:text-h3 font-bold mt-1 ${
                proposal.cost_delta <= 0 ? 'text-success dark:text-success-text' : 'text-danger dark:text-danger-text'
              }`}
            >
              {formatDeltaCurrency(proposal.cost_delta, currency)}
            </div>
          </div>

          {/* Time Delta */}
          <div className="card-surface p-3.5 text-center flex flex-col justify-between">
            <span className="text-caption uppercase tracking-wider text-text-muted flex items-center justify-center gap-1 font-semibold">
              <Clock size={16} strokeWidth={1.75} className="text-primary" />
              Time Delta
            </span>
            <div className="tabular-mono text-small sm:text-h3 font-bold text-text-primary mt-1">
              {proposal.time_delta_min > 0 ? `+${proposal.time_delta_min}m` : `${proposal.time_delta_min}m`}
            </div>
          </div>

          {/* Items Changed */}
          <div className="card-surface p-3.5 text-center flex flex-col justify-between">
            <span className="text-caption uppercase tracking-wider text-text-muted flex items-center justify-center gap-1 font-semibold">
              <Layers size={16} strokeWidth={1.75} className="text-accent" />
              Items Changed
            </span>
            <div className="tabular-mono text-small sm:text-h3 font-bold text-text-primary mt-1">
              {proposal.items_changed}
            </div>
          </div>
        </div>

        {/* Diff View */}
        <div className="space-y-2">
          <h4 className="text-caption uppercase tracking-wider text-text-muted font-semibold">
            Detailed Comparison
          </h4>
          <DiffView diff={proposal.diff} currency={currency} />
        </div>

        {/* Sticky footer with actions */}
        <div className="pt-4 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3 sticky bottom-0 bg-surface/95 backdrop-blur-sm py-2 -mx-5 px-5 sm:-mx-6 sm:px-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDecision('alternatives')}
            disabled={isPending}
            className="w-full sm:w-auto gap-1.5 text-text-secondary hover:text-text-primary order-3 sm:order-1"
          >
            <Shuffle size={16} strokeWidth={1.75} />
            <span>Show alternatives</span>
          </Button>

          <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end order-1 sm:order-2">
            <Button
              variant="outline"
              size="md"
              onClick={() => handleDecision('reject')}
              disabled={isPending}
              className="flex-1 sm:flex-none gap-2 text-text-primary"
            >
              <X size={16} strokeWidth={1.75} />
              <span>Reject</span>
            </Button>

            <Button
              variant="primary"
              size="md"
              onClick={() => handleDecision('approve')}
              disabled={isPending}
              className="flex-1 sm:flex-none gap-2 shadow-sm font-semibold"
            >
              {isPending ? (
                <>
                  <Loader2 size={16} strokeWidth={1.75} className="animate-spin" />
                  <span>Applying changes...</span>
                </>
              ) : (
                <>
                  <Check size={16} strokeWidth={1.75} />
                  <span>Approve changes</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
