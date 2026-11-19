import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useRunStream } from './useRunStream';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as sseModule from '@/lib/sse';
import { AgentEvent } from '@/types/contract';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = 'QueryClientTestWrapper';
  return Wrapper;
};

describe('useRunStream', () => {
  it('subscribes to stream and appends events', () => {
    let capturedCallback: ((event: AgentEvent) => void) | null = null;

    vi.spyOn(sseModule, 'subscribeToRunStream').mockImplementation(({ onEvent }) => {
      capturedCallback = onEvent;
      return () => {};
    });

    const { result } = renderHook(() => useRunStream('run-test-123'), {
      wrapper: createWrapper(),
    });

    expect(result.current.isRunning).toBe(true);

    // Emit first event
    act(() => {
      capturedCallback?.({
        seq: 1,
        type: 'step',
        node: 'researcher',
        message: 'Searching places',
        status: 'running',
      });
    });

    expect(result.current.events).toHaveLength(1);
    expect(result.current.events[0].status).toBe('running');

    // Emit status update for same node + message -> updates row in place
    act(() => {
      capturedCallback?.({
        seq: 2,
        type: 'step',
        node: 'researcher',
        message: 'Searching places',
        status: 'done',
      });
    });

    expect(result.current.events).toHaveLength(1);
    expect(result.current.events[0].status).toBe('done');
  });

  it('triggers onProposal callback when proposal event is received', () => {
    let capturedCallback: ((event: AgentEvent) => void) | null = null;
    const onProposal = vi.fn();

    vi.spyOn(sseModule, 'subscribeToRunStream').mockImplementation(({ onEvent }) => {
      capturedCallback = onEvent;
      return () => {};
    });

    renderHook(() => useRunStream('run-prop-123', { onProposal }), {
      wrapper: createWrapper(),
    });

    act(() => {
      capturedCallback?.({
        seq: 3,
        type: 'proposal',
        node: 'build_proposal',
        message: 'Proposal created',
        status: 'done',
        payload: { proposal_id: 'prop-999' },
      });
    });

    expect(onProposal).toHaveBeenCalledWith('prop-999');
  });

  it('stops running and handles error event', () => {
    let capturedCallback: ((event: AgentEvent) => void) | null = null;

    vi.spyOn(sseModule, 'subscribeToRunStream').mockImplementation(({ onEvent }) => {
      capturedCallback = onEvent;
      return () => {};
    });

    const { result } = renderHook(() => useRunStream('run-err-123'), {
      wrapper: createWrapper(),
    });

    act(() => {
      capturedCallback?.({
        seq: 4,
        type: 'error',
        payload: { message: 'Weather service unavailable' },
      });
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBe('Weather service unavailable');
  });
});
