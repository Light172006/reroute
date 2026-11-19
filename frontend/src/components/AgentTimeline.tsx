'use client';

import React from 'react';
import { AgentEvent } from '@/types/contract';
import { CheckCircle2, XCircle, Loader2, PlayCircle, Bot, Wrench } from 'lucide-react';

interface AgentTimelineProps {
  events: AgentEvent[];
  isRunning?: boolean;
  className?: string;
}

export function AgentTimeline({ events, isRunning = false, className = '' }: AgentTimelineProps) {
  // Filter for displayable timeline items
  const displayable = (events || []).filter(
    (e) => e.type !== 'token' && (e.message || e.node || e.type === 'error')
  );

  const [liveAnnouncement, setLiveAnnouncement] = React.useState('');
  const lastAnnouncedTimeRef = React.useRef(0);

  React.useEffect(() => {
    const latest = displayable[displayable.length - 1];
    if (!latest) return;
    const now = Date.now();
    if (
      now - lastAnnouncedTimeRef.current > 1500 ||
      latest.status === 'done' ||
      latest.type === 'error'
    ) {
      lastAnnouncedTimeRef.current = now;
      setLiveAnnouncement(latest.message || latest.node || 'Agent step updated');
    }
  }, [displayable]);

  if (!events || events.length === 0) {
    return (
      <div className="p-6 text-center text-small text-text-muted space-y-2">
        <Bot size={24} strokeWidth={1.75} className="mx-auto opacity-50" />
        <p>No active background operations.</p>
      </div>
    );
  }

  return (
    <div
      aria-label="Agent execution activity timeline"
      className={`space-y-4 ${className}`}
    >
      {/* Screen reader live announcement region with throttle */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {liveAnnouncement}
      </div>
      <div className="flex items-center justify-between pb-1 border-b border-border">
        <span className="text-caption uppercase tracking-wider text-text-muted font-semibold">
          Agent Execution Activity
        </span>
        {isRunning && (
          <span className="flex items-center gap-1.5 text-primary text-caption font-medium">
            <Loader2 size={16} strokeWidth={1.75} className="animate-spin" />
            <span>Streaming</span>
          </span>
        )}
      </div>

      <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
        {displayable.map((event, idx) => {
          const isDone = event.status === 'done' || event.type === 'done';
          const isFailed = event.status === 'failed' || event.type === 'error';
          const isEventRunning = event.status === 'running';
          const isTool = event.type === 'tool_call' || event.type === 'tool_result';

          return (
            <div
              key={event.seq || idx}
              className="relative flex items-start justify-between gap-3 text-small animate-fade-up"
            >
              {/* Stepper Node Status Icon */}
              <div className="absolute -left-6 top-0.5 shrink-0 bg-surface rounded-full">
                {isFailed ? (
                  <XCircle size={16} strokeWidth={1.75} className="text-danger" aria-label="Failed" />
                ) : isEventRunning ? (
                  <Loader2 size={16} strokeWidth={1.75} className="text-primary animate-spin" aria-label="Running" />
                ) : isDone ? (
                  <CheckCircle2 size={16} strokeWidth={1.75} className="text-success" aria-label="Completed" />
                ) : (
                  <PlayCircle size={16} strokeWidth={1.75} className="text-text-muted" aria-label="Queued" />
                )}
              </div>

              {/* Main Info */}
              <div className="flex-1 min-w-0 pr-2">
                <div className="flex items-center gap-2">
                  {event.node && (
                    <span className="font-mono text-caption uppercase px-1.5 py-0.5 rounded bg-surface-alt text-text-secondary font-semibold">
                      {event.node}
                    </span>
                  )}
                  {isTool && (
                    <Wrench size={16} strokeWidth={1.75} className="text-text-muted" aria-label="Tool execution" />
                  )}
                  <p
                    className={`font-medium ${
                      isFailed
                        ? 'text-danger font-semibold'
                        : isEventRunning
                        ? 'text-primary font-semibold'
                        : 'text-text-primary'
                    }`}
                  >
                    {event.message || (event.type === 'error' ? 'An error occurred' : 'Running step...')}
                  </p>
                </div>

                {typeof event.payload?.summary === 'string' && (
                  <p className="text-caption text-text-secondary mt-0.5">
                    {event.payload.summary}
                  </p>
                )}
              </div>

              {/* Latency on Right */}
              {typeof event.payload?.latency_ms === 'number' ? (
                <span className="tabular-mono text-caption text-text-muted shrink-0">
                  {event.payload.latency_ms}ms
                </span>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
