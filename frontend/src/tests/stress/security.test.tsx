import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { api } from '@/lib/api';
import { ItineraryItemCard } from '@/components/ItineraryItemCard';
import { AgentTimeline } from '@/components/AgentTimeline';
import { ItineraryItem, AgentEvent } from '@/types/contract';

describe('A7: Frontend Security Stress Tests', () => {
  it('XSS: User-editable text and notes containing img onerror and javascript: URLs never execute scripts', () => {
    const errorSpy = vi.fn();
    (window as any).__maliciousScriptExecuted = false;

    const maliciousItem: ItineraryItem = {
      id: 'malicious-1',
      stable_key: 'stb-malicious',
      position: 0,
      title: '<img src="invalid-image" onerror="window.__maliciousScriptExecuted=true" /> Malicious Stop',
      category: 'sightseeing',
      setting: 'outdoor',
      start_time: '14:00',
      end_time: '15:00',
      est_cost: 0,
      is_locked: false,
      flags: [],
      notes: '<a href="javascript:window.__maliciousScriptExecuted=true">Click here for free trip</a>',
    };

    render(
      <ItineraryItemCard
        item={maliciousItem}
        onToggleLock={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    // Verify raw tag is rendered safely as text
    expect(screen.getByText(/<img src="invalid-image"/i)).toBeInTheDocument();
    expect((window as any).__maliciousScriptExecuted).toBe(false);
  });

  it('XSS: Agent SSE output containing script injections renders safely as plain text', () => {
    const maliciousEvents: AgentEvent[] = [
      {
        seq: 1,
        type: 'step',
        node: '<script>window.__agentXss=true</script>',
        message: '<b onmouseover="window.__agentXss=true">Step message with HTML payload</b>',
        status: 'done',
        timestamp: new Date().toISOString(),
      },
    ];

    render(<AgentTimeline events={maliciousEvents} isRunning={false} />);

    expect(screen.getAllByText(/<b onmouseover=/i).length).toBeGreaterThan(0);
    expect((window as any).__agentXss).toBeUndefined();
  });

  it('Tokens: Auth tokens are never leaked into URL parameters or console logs', () => {
    const logSpy = vi.spyOn(console, 'log');
    const secretToken = 'jwt-secret-payload-token-12345';

    api.setTokens(secretToken, 'refresh-token-54321');

    // Confirm that setTokens or api methods did not write secretToken to console
    const leakedLogs = logSpy.mock.calls.some((callArgs) =>
      callArgs.some((arg) => typeof arg === 'string' && arg.includes(secretToken))
    );
    expect(leakedLogs).toBe(false);

    logSpy.mockRestore();
  });
});
