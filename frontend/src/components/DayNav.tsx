'use client';

import React from 'react';
import { useUIStore } from '@/hooks/useUIStore';
import { ItineraryDay, ProposalResponse } from '@/types/contract';
import { Calendar, AlertCircle } from 'lucide-react';

interface DayNavProps {
  days: ItineraryDay[];
  pendingProposal?: ProposalResponse | null;
  className?: string;
  isMobileChips?: boolean;
}

export function DayNav({
  days,
  pendingProposal,
  className = '',
  isMobileChips = false,
}: DayNavProps) {
  const { selectedDayIndex, setSelectedDayIndex } = useUIStore();

  // Find which days have pending disruptions
  const disruptedDays = new Set<number>();
  if (pendingProposal?.diff) {
    pendingProposal.diff.forEach((d) => disruptedDays.add(d.day));
  }
  if (pendingProposal?.disruptions) {
    pendingProposal.disruptions.forEach((d) => {
      if (d.day_index) disruptedDays.add(d.day_index);
    });
  }

  if (isMobileChips) {
    return (
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none snap-x snap-mandatory px-4 md:hidden">
        {days.map((day) => {
          const isSelected = selectedDayIndex === day.day_index;
          const hasDisruption = disruptedDays.has(day.day_index);

          return (
            <button
              key={day.day_index}
              onClick={() => setSelectedDayIndex(day.day_index)}
              className={`snap-start flex items-center gap-2 px-4 py-2 rounded-pill text-small font-semibold whitespace-nowrap transition-all border ${
                isSelected
                  ? 'btn-primary-gradient text-on-primary border-transparent shadow-sm'
                  : 'bg-surface text-text-primary border-border hover:bg-surface-alt'
              }`}
            >
              <span>Day {day.day_index}</span>
              {hasDisruption && (
                <span className="relative flex h-2 w-2">
                  <span className="attention-pulse absolute inline-flex h-full w-full rounded-full bg-accent opacity-80" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-accent ring-2 ring-surface" />
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <nav className={`space-y-1.5 ${className}`} aria-label="Trip days navigation">
      <div className="px-3 pb-2 text-caption uppercase tracking-wider text-text-muted font-semibold flex items-center justify-between">
        <span>Itinerary Days</span>
        <Calendar size={16} strokeWidth={1.75} aria-hidden="true" />
      </div>

      <div className="space-y-1">
        {days.map((day) => {
          const isSelected = selectedDayIndex === day.day_index;
          const hasDisruption = disruptedDays.has(day.day_index);
          const dateObj = new Date(day.date);

          return (
            <button
              key={day.day_index}
              onClick={() => setSelectedDayIndex(day.day_index)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-input text-small transition-all text-left ${
                isSelected
                  ? 'bg-primary/10 text-primary font-semibold border border-primary/20 shadow-xs'
                  : 'text-text-secondary hover:bg-surface-alt hover:text-text-primary'
              }`}
            >
              <div className="flex flex-col">
                <span className="font-semibold text-text-primary">
                  Day {day.day_index}
                </span>
                <span className="text-caption text-text-muted font-normal">
                  {dateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                </span>
              </div>

              {hasDisruption && (
                <div className="flex items-center gap-1.5">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="attention-pulse absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-accent ring-2 ring-surface" />
                  </span>
                  <AlertCircle size={16} strokeWidth={1.75} className="text-accent" aria-label="Disruption alert" />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
