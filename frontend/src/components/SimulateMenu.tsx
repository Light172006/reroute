'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import {
  CloudRain,
  DoorClosed,
  Train,
  TrendingUp,
  ChevronDown,
  Zap,
  Loader2,
} from 'lucide-react';

interface SimulateMenuProps {
  tripId: string;
  onSimulateStarted: (runId: string) => void;
  className?: string;
}

export function SimulateMenu({ tripId, onSimulateStarted, className = '' }: SimulateMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleSimulate = async (type: 'weather' | 'closure' | 'delay' | 'budget_overrun') => {
    setIsLoading(true);
    setIsOpen(false);
    try {
      const res = await api.simulateDisruption({
        trip_id: tripId,
        type,
        day_index: 2,
      });
      onSimulateStarted(res.run_id);
    } catch (err) {
      console.error('Failed to trigger simulation:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`relative inline-block text-left ${className}`} ref={dropdownRef}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="gap-2 text-xs font-semibold text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/40 border border-amber-200/80 dark:border-amber-800/60"
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-accent" strokeWidth={1.75} />
        ) : (
          <Zap className="h-4 w-4 text-accent" strokeWidth={1.75} />
        )}
        Simulate disruption
        <ChevronDown className="h-4 w-4 opacity-60 ml-0.5" strokeWidth={1.75} />
      </Button>

      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-64 rounded-card bg-surface border border-border shadow-xl z-50 py-2 focus:outline-none animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted border-b border-border">
            Demo Disruption Scenarios
          </div>

          <div className="py-1">
            <button
              role="menuitem"
              onClick={() => handleSimulate('weather')}
              className="w-full flex items-start gap-3 px-3.5 py-2.5 text-xs text-left text-text-secondary hover:bg-surface-alt transition-colors"
            >
              <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
                <CloudRain className="h-4 w-4" strokeWidth={1.75} />
              </div>
              <div>
                <div className="font-semibold text-text-primary">Rain on Day 2</div>
                <div className="text-[11px] text-text-muted">80% rain 2-6pm, outdoor stops</div>
              </div>
            </button>

            <button
              role="menuitem"
              onClick={() => handleSimulate('closure')}
              className="w-full flex items-start gap-3 px-3.5 py-2.5 text-xs text-left text-text-secondary hover:bg-surface-alt transition-colors"
            >
              <div className="h-8 w-8 rounded-full bg-orange-100 dark:bg-orange-950/60 text-orange-600 dark:text-orange-400 flex items-center justify-center shrink-0 mt-0.5">
                <DoorClosed className="h-4 w-4" strokeWidth={1.75} />
              </div>
              <div>
                <div className="font-semibold text-text-primary">Attraction closed</div>
                <div className="text-[11px] text-text-muted">Ropeway safety maintenance</div>
              </div>
            </button>

            <button
              role="menuitem"
              onClick={() => handleSimulate('delay')}
              className="w-full flex items-start gap-3 px-3.5 py-2.5 text-xs text-left text-text-secondary hover:bg-surface-alt transition-colors"
            >
              <div className="h-8 w-8 rounded-full bg-purple-100 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0 mt-0.5">
                <Train className="h-4 w-4" strokeWidth={1.75} />
              </div>
              <div>
                <div className="font-semibold text-text-primary">Train delayed 2h</div>
                <div className="text-[11px] text-text-muted">Transit lag shifting day schedule</div>
              </div>
            </button>

            <button
              role="menuitem"
              onClick={() => handleSimulate('budget_overrun')}
              className="w-full flex items-start gap-3 px-3.5 py-2.5 text-xs text-left text-text-secondary hover:bg-surface-alt transition-colors"
            >
              <div className="h-8 w-8 rounded-full bg-red-100 dark:bg-red-950/60 text-red-600 dark:text-red-400 flex items-center justify-center shrink-0 mt-0.5">
                <TrendingUp className="h-4 w-4" strokeWidth={1.75} />
              </div>
              <div>
                <div className="font-semibold text-text-primary">Budget overrun</div>
                <div className="text-[11px] text-text-muted">Expenses exceed plan by 14%</div>
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
