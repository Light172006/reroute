import { useState, useEffect, useCallback, useRef } from 'react';
import { AgentEvent } from '@/types/contract';
import { subscribeToRunStream } from '@/lib/sse';
import { useQueryClient } from '@tanstack/react-query';
import { useUIStore } from '@/hooks/useUIStore';

const MAX_EVENTS = 300;
const MAX_RETRY_ATTEMPTS = 5;

interface UseRunStreamOptions {
  tripId?: string;
  onDone?: () => void;
  onProposal?: (proposalId: string) => void;
  onError?: (error: Error | unknown) => void;
}

export function useRunStream(runId?: string | null, options: UseRunStreamOptions = {}) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState<string>('');

  const lastSeqRef = useRef<number | null>(null);
  const runIdRef = useRef<string | null>(runId || null);
  runIdRef.current = runId || null;

  const retryCountRef = useRef<number>(0);
  const retryTimerRef = useRef<NodeJS.Timeout | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const fallbackToastShownRef = useRef<boolean>(false);

  const queryClient = useQueryClient();
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const handleEvent = useCallback(
    (event: AgentEvent) => {
      // Validate event payload structure
      if (!event || typeof event !== 'object') return;

      if (typeof event.seq === 'number') {
        lastSeqRef.current = Math.max(lastSeqRef.current ?? 0, event.seq);
      }

      // Token streaming concatenation
      if (event.type === 'token') {
        const textChunk = typeof event.payload?.text === 'string' ? event.payload.text : '';
        if (textChunk) {
          setStreamingText((prev) => prev + textChunk);
        }
        return;
      }

      // Fallback model switch notice (shown once per run)
      if (event.type === 'llm_call' && event.payload?.fallback === true) {
        if (!fallbackToastShownRef.current) {
          fallbackToastShownRef.current = true;
          useUIStore.getState().setToast({
            type: 'warning',
            text: 'Taking longer than usual, switching model',
          });
        }
      }

      setEvents((prev) => {
        // If event with this seq already exists in list
        if (typeof event.seq === 'number') {
          const existingSeqIdx = prev.findIndex((e) => e.seq === event.seq);
          if (existingSeqIdx !== -1) {
            // If status changed or payload updated, update in place
            if (event.status && prev[existingSeqIdx].status !== event.status) {
              const updated = [...prev];
              updated[existingSeqIdx] = {
                ...updated[existingSeqIdx],
                status: event.status,
                payload: { ...updated[existingSeqIdx].payload, ...event.payload },
              };
              return updated;
            }
            // Exact duplicate event: ignore
            return prev;
          }
        }

        // If same node + message exists and status changed, update it in place
        if (event.node && event.message) {
          const existingNodeIndex = prev.findIndex(
            (e) => e.node === event.node && e.message === event.message
          );

          if (existingNodeIndex !== -1 && event.status) {
            const updated = [...prev];
            updated[existingNodeIndex] = {
              ...updated[existingNodeIndex],
              status: event.status,
              payload: { ...updated[existingNodeIndex].payload, ...event.payload },
            };
            return updated;
          }
        }

        // Append and preserve sequence ordering
        const next = [...prev, event];
        if (next.some((e) => typeof e.seq === 'number')) {
          next.sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0));
        }

        // Strictly cap events to prevent unbounded memory growth during floods
        if (next.length > MAX_EVENTS) {
          return next.slice(next.length - MAX_EVENTS);
        }

        return next;
      });

      if (event.type === 'proposal') {
        const propId = typeof event.payload?.proposal_id === 'string' ? event.payload.proposal_id : undefined;
        if (propId && optionsRef.current.onProposal) {
          optionsRef.current.onProposal(propId);
        }
        if (optionsRef.current.tripId) {
          queryClient.invalidateQueries({ queryKey: ['proposals', optionsRef.current.tripId] });
          queryClient.invalidateQueries({ queryKey: ['trip', optionsRef.current.tripId] });
        }
      }

      if (event.type === 'done') {
        setIsRunning(false);
        setIsDone(true);
        retryCountRef.current = 0;
        if (optionsRef.current.tripId) {
          queryClient.invalidateQueries({ queryKey: ['itinerary', optionsRef.current.tripId] });
          queryClient.invalidateQueries({ queryKey: ['versions', optionsRef.current.tripId] });
          queryClient.invalidateQueries({ queryKey: ['trip', optionsRef.current.tripId] });
        }
        optionsRef.current.onDone?.();
      }

      if (event.type === 'error') {
        const isRecoverable = event.payload?.recoverable === true;
        const errMsg = typeof event.payload?.message === 'string' ? event.payload.message : 'Agent encountered an error';
        if (!isRecoverable) {
          setIsRunning(false);
          setError(errMsg);
        } else {
          useUIStore.getState().setToast({
            type: 'warning',
            text: errMsg,
          });
        }
        optionsRef.current.onError?.(event.payload);
      }
    },
    [queryClient]
  );

  const startStream = useCallback(
    (targetRunId: string) => {
      // Clear previous timer if any
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }

      setIsRunning(true);
      setIsDone(false);
      setError(null);

      const unsubscribe = subscribeToRunStream({
        runId: targetRunId,
        lastEventId: lastSeqRef.current ? String(lastSeqRef.current) : undefined,
        onEvent: handleEvent,
        onError: (err) => {
          // Exponential backoff reconnect
          if (retryCountRef.current < MAX_RETRY_ATTEMPTS) {
            const delay = Math.min(500 * Math.pow(2, retryCountRef.current), 5000);
            retryCountRef.current += 1;
            retryTimerRef.current = setTimeout(() => {
              if (runIdRef.current) {
                startStream(runIdRef.current);
              }
            }, delay);
          } else {
            setIsRunning(false);
            setError('Connection lost after repeated attempts. Please retry.');
            optionsRef.current.onError?.(err);
          }
        },
        onDone: () => {
          setIsRunning(false);
          setIsDone(true);
          retryCountRef.current = 0;
        },
      });

      unsubscribeRef.current = unsubscribe;
      return unsubscribe;
    },
    [handleEvent]
  );

  useEffect(() => {
    if (!runId) {
      setEvents([]);
      setIsRunning(false);
      setIsDone(false);
      setError(null);
      setStreamingText('');
      retryCountRef.current = 0;
      fallbackToastShownRef.current = false;
      return;
    }

    const unsubscribe = startStream(runId);

    return () => {
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
      unsubscribe();
    };
  }, [runId, startStream]);

  const retry = useCallback(() => {
    if (runId) {
      retryCountRef.current = 0;
      setError(null);
      startStream(runId);
    }
  }, [runId, startStream]);

  const reset = useCallback(() => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }
    setEvents([]);
    setIsRunning(false);
    setIsDone(false);
    setError(null);
    setStreamingText('');
    lastSeqRef.current = null;
    retryCountRef.current = 0;
    fallbackToastShownRef.current = false;
  }, []);

  return {
    events,
    isRunning,
    isDone,
    error,
    streamingText,
    retry,
    reset,
  };
}
