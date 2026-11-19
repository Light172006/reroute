'use client';

import React from 'react';
import { ProposalResponse } from '@/types/contract';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CloudRain, Clock, ArrowRight } from 'lucide-react';

interface DisruptionBannerProps {
  proposal: ProposalResponse;
  onReview: () => void;
  className?: string;
}

export function DisruptionBanner({ proposal, onReview, className = '' }: DisruptionBannerProps) {
  const disruptionType = proposal.disruptions?.[0]?.type || 'weather';

  const getDisruptionIcon = () => {
    switch (disruptionType) {
      case 'weather':
        return CloudRain;
      case 'delay':
        return Clock;
      case 'closure':
      case 'budget_overrun':
      default:
        return AlertTriangle;
    }
  };

  const DisruptionIcon = getDisruptionIcon();

  return (
    <div
      role="alert"
      className={`rounded-card border border-accent-border bg-accent-bg p-4 sm:p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-slide-down ${className}`}
    >
      <div className="flex items-start sm:items-center gap-3.5">
        {/* Solid amber circle */}
        <div className="h-10 w-10 rounded-full bg-accent text-black flex items-center justify-center shrink-0 shadow-xs">
          <DisruptionIcon size={20} strokeWidth={1.75} aria-hidden="true" />
        </div>

        <div className="space-y-1">
          <h4 className="text-small sm:text-body font-bold text-accent-text">
            {proposal.reason}
          </h4>
          <p className="text-caption text-accent-text/90">
            {proposal.explanation || `${proposal.items_changed} stops affected. Reroute prepared an indoor alternative.`}
          </p>
        </div>
      </div>

      <div className="shrink-0 flex items-center justify-end w-full sm:w-auto">
        <Button
          onClick={onReview}
          variant="accent"
          size="sm"
          className="w-full sm:w-auto gap-2 shadow-xs font-semibold"
        >
          <span>Review changes</span>
          <ArrowRight size={16} strokeWidth={1.75} aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
