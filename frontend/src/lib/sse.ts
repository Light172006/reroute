import { AgentEvent } from '@/types/contract';
import { mockStore } from '@/mocks/handlers';
import { fetchEventSource } from '@microsoft/fetch-event-source';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === 'true';

export interface SSEStreamOptions {
  runId: string;
  onEvent: (event: AgentEvent) => void;
  onError: (error: Error | unknown) => void;
  onDone?: () => void;
  lastEventId?: string;
  token?: string | null;
}

export function subscribeToRunStream(options: SSEStreamOptions): () => void {
  const { runId, onEvent, onError, onDone, lastEventId, token } = options;

  if (USE_MOCKS) {
    const unsubscribe = mockStore.subscribeRun(
      runId,
      (event) => {
        onEvent(event);
        if (event.type === 'done') {
          onDone?.();
        }
      },
      lastEventId,
      onError
    );
    return unsubscribe;
  }

  const ctrl = new AbortController();

  fetchEventSource(`${BASE_URL}/agent/runs/${runId}/stream`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(lastEventId ? { 'Last-Event-ID': lastEventId } : {}),
    },
    signal: ctrl.signal,
    onmessage(msg) {
      if (msg.event === 'ping') return;
      try {
        const data: AgentEvent = JSON.parse(msg.data);
        if (msg.id) {
          data.seq = parseInt(msg.id, 10);
        }
        onEvent(data);
        if (data.type === 'done') {
          onDone?.();
          ctrl.abort();
        }
      } catch (err) {
        console.error('Error parsing SSE event data:', err);
      }
    },
    onerror(err) {
      onError(err);
      throw err; // Stop retrying on fatal
    },
  });

  return () => {
    ctrl.abort();
  };
}
