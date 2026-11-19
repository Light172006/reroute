import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useRunStream } from '@/hooks/useRunStream';
import { mockStore } from '@/mocks/handlers';
import { AgentEvent } from '@/types/contract';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useUIStore } from '@/hooks/useUIStore';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = 'TestQueryClientWrapper';
  return Wrapper;
}

describe('A2: SSE and Real-time Stream Stress', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useUIStore.setState({ toastMessage: null });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('Flood: streams 2,000 events without duplicate rows or unbounded memory growth', () => {
    const runId = 'run-flood-test';
    const wrapper = createWrapper();
    const { result } = renderHook(() => useRunStream(runId), { wrapper });

    act(() => {
      // Flood with 2,000 events
      for (let i = 1; i <= 2000; i++) {
        mockStore.emitRunEvent(runId, {
          seq: i,
          type: 'step',
          node: `step-node-${i}`,
          message: `Processing step number ${i}`,
          status: 'running',
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Events must be strictly capped (MAX_EVENTS = 300) to prevent unbounded memory growth
    expect(result.current.events.length).toBeLessThanOrEqual(300);
    expect(result.current.events.length).toBeGreaterThan(0);

    // Verify latest event sequence is maintained
    const latestEvent = result.current.events[result.current.events.length - 1];
    expect(latestEvent.seq).toBe(2000);
  });

  it('Out of order and duplicate events: preserves sorted order and deduplicates identical events', () => {
    const runId = 'run-out-of-order';
    const wrapper = createWrapper();
    const { result } = renderHook(() => useRunStream(runId), { wrapper });

    act(() => {
      // Send seq 5 first
      mockStore.emitRunEvent(runId, {
        seq: 5,
        type: 'step',
        node: 'route_optimizer',
        message: 'Optimizing geo-spatial route clusters',
        status: 'running',
        timestamp: new Date().toISOString(),
      });

      // Send seq 4 later
      mockStore.emitRunEvent(runId, {
        seq: 4,
        type: 'step',
        node: 'weather_checker',
        message: 'Checking rain telemetry',
        status: 'running',
        timestamp: new Date().toISOString(),
      });

      // Send duplicate seq 4 (exact duplicate)
      mockStore.emitRunEvent(runId, {
        seq: 4,
        type: 'step',
        node: 'weather_checker',
        message: 'Checking rain telemetry',
        status: 'running',
        timestamp: new Date().toISOString(),
      });
    });

    // Must not have duplicate seq 4
    const seq4Items = result.current.events.filter((e) => e.seq === 4);
    expect(seq4Items.length).toBe(1);

    // Final order must be seq 4 then seq 5
    expect(result.current.events[0].seq).toBe(4);
    expect(result.current.events[1].seq).toBe(5);
  });

  it('Disconnect and resume: reconnects with last seq and plays missed events once', () => {
    const runId = 'run-disconnect-resume';
    mockStore.runs[runId] = {
      trip_id: 'trip-test',
      type: 'plan',
      status: 'running',
      events: [
        { seq: 1, type: 'step', message: 'Step 1', timestamp: new Date().toISOString() },
        { seq: 2, type: 'step', message: 'Step 2', timestamp: new Date().toISOString() },
        { seq: 3, type: 'step', message: 'Step 3', timestamp: new Date().toISOString() },
        { seq: 4, type: 'step', message: 'Step 4', timestamp: new Date().toISOString() },
        { seq: 5, type: 'done', message: 'Finished', timestamp: new Date().toISOString() },
      ],
    };

    const receivedEvents: AgentEvent[] = [];
    // Start initial connection
    const unsub1 = mockStore.subscribeRun(runId, (ev) => receivedEvents.push(ev));
    act(() => {
      vi.advanceTimersByTime(110); // Receives seq 1 and 2
    });
    unsub1(); // Drop connection mid-run

    expect(receivedEvents.length).toBe(2);
    expect(receivedEvents[1].seq).toBe(2);

    // Reconnect with lastEventId = "2"
    const resumedEvents: AgentEvent[] = [];
    const unsub2 = mockStore.subscribeRun(
      runId,
      (ev) => resumedEvents.push(ev),
      String(receivedEvents[1].seq)
    );

    act(() => {
      vi.advanceTimersByTime(250); // Finish remaining events
    });
    unsub2();

    // Missed events (seq 3, 4, 5) must be played exactly once
    expect(resumedEvents.map((e) => e.seq)).toEqual([3, 4, 5]);
  });

  it('Repeated drops: backs off exponentially and stops after limit with visible error and retry', () => {
    const runId = 'run-repeated-drops';
    const wrapper = createWrapper();
    const onError = vi.fn();
    const { result } = renderHook(() => useRunStream(runId, { onError }), { wrapper });

    expect(result.current.isRunning).toBe(true);

    // Simulate consecutive connection drop errors and advance backoff timers
    for (let i = 0; i < 6; i++) {
      act(() => {
        mockStore.emitRunError(runId, new Error('Drop error'));
      });
      act(() => {
        vi.runOnlyPendingTimers();
      });
    }

    // Must have stopped running and show clear error
    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toContain('Connection lost after repeated attempts');

    // User can manually retry
    act(() => {
      result.current.retry();
    });
    expect(result.current.error).toBeNull();
    expect(result.current.isRunning).toBe(true);
  });

  it('Malformed payloads: unknown types, null payloads, and huge payloads do not crash the hook', () => {
    const runId = 'run-malformed-payloads';
    const wrapper = createWrapper();
    const { result } = renderHook(() => useRunStream(runId), { wrapper });

    act(() => {
      // 1. Unknown type
      mockStore.emitRunEvent(runId, {
        seq: 10,
        type: 'unrecognized_custom_type' as any,
        message: 'Unknown event',
        timestamp: new Date().toISOString(),
      });

      // 2. Missing/null payload
      mockStore.emitRunEvent(runId, {
        seq: 11,
        type: 'step',
        payload: null as any,
        timestamp: new Date().toISOString(),
      });

      // 3. 1 MB huge payload string
      const hugeString = 'X'.repeat(1024 * 1024);
      mockStore.emitRunEvent(runId, {
        seq: 12,
        type: 'tool_result',
        node: 'search_cache',
        message: 'Cached search response',
        payload: { big_data: hugeString },
        timestamp: new Date().toISOString(),
      });
    });

    expect(result.current.events.length).toBe(3);
    expect(result.current.error).toBeNull();
  });

  it('Event types: error with recoverable true vs false behaves differently', () => {
    const runId = 'run-error-types';
    const wrapper = createWrapper();
    const { result } = renderHook(() => useRunStream(runId), { wrapper });

    // 1. Recoverable error: does not abort isRunning
    act(() => {
      mockStore.emitRunEvent(runId, {
        seq: 20,
        type: 'error',
        payload: {
          code: 'RATE_LIMIT_WARNING',
          message: 'Secondary provider throttled, retrying with fallback model',
          recoverable: true,
        },
        timestamp: new Date().toISOString(),
      });
    });

    expect(result.current.isRunning).toBe(true);
    expect(result.current.error).toBeNull();
    expect(useUIStore.getState().toastMessage?.type).toBe('warning');

    // 2. Non-recoverable error: marks stream as failed
    act(() => {
      mockStore.emitRunEvent(runId, {
        seq: 21,
        type: 'error',
        payload: {
          code: 'INTERNAL_ERROR',
          message: 'Fatal pipeline execution breakdown',
          recoverable: false,
        },
        timestamp: new Date().toISOString(),
      });
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toContain('Fatal pipeline execution breakdown');
  });

  it('Fallback notice: llm_call with fallback: true fires toast once per run', () => {
    const runId = 'run-fallback-toast';
    const wrapper = createWrapper();
    renderHook(() => useRunStream(runId), { wrapper });

    act(() => {
      // Event 1 with fallback
      mockStore.emitRunEvent(runId, {
        seq: 30,
        type: 'llm_call',
        node: 'planner_llm',
        payload: { fallback: true, model: 'secondary-model' },
        timestamp: new Date().toISOString(),
      });
    });

    expect(useUIStore.getState().toastMessage?.text).toBe('Taking longer than usual, switching model');

    // Clear toast
    act(() => {
      useUIStore.setState({ toastMessage: null });
    });

    act(() => {
      // Subsequent fallback events in same run must not spam toast
      mockStore.emitRunEvent(runId, {
        seq: 31,
        type: 'llm_call',
        node: 'synthesizer_llm',
        payload: { fallback: true, model: 'secondary-model' },
        timestamp: new Date().toISOString(),
      });
    });

    expect(useUIStore.getState().toastMessage).toBeNull();
  });

  it('Lifecycle: navigating away mid-stream leaves zero leaked connections', () => {
    const initialConnections = mockStore.activeConnectionsCount;

    // Simulate opening 10 trips in sequence and navigating away
    for (let i = 1; i <= 10; i++) {
      const wrapper = createWrapper();
      const { unmount } = renderHook(() => useRunStream(`run-trip-${i}`), { wrapper });
      unmount();
    }

    expect(mockStore.activeConnectionsCount).toBe(initialConnections);
  });

  it('Token streaming: 500 token events accumulate smoothly and equal full concatenation', () => {
    const runId = 'run-tokens-test';
    const wrapper = createWrapper();
    const { result } = renderHook(() => useRunStream(runId), { wrapper });

    const tokens: string[] = [];
    for (let i = 0; i < 500; i++) {
      tokens.push(`word${i} `);
    }
    const expectedFullText = tokens.join('');

    act(() => {
      tokens.forEach((token, idx) => {
        mockStore.emitRunEvent(runId, {
          seq: idx + 1,
          type: 'token',
          payload: { text: token },
          timestamp: new Date().toISOString(),
        });
      });
    });

    expect(result.current.streamingText).toBe(expectedFullText);
  });
});
