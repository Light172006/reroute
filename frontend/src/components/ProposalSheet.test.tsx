import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ProposalSheet } from './ProposalSheet';
import { ProposalResponse } from '@/types/contract';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { api } from '@/lib/api';

const mockProposal: ProposalResponse = {
  id: 'prop-test-01',
  trip_id: 'trip-test-01',
  run_id: 'run-test-01',
  base_version_id: 'ver-1',
  status: 'pending',
  reason: 'Rain expected Day 2, 2-6pm (80%). 2 outdoor stops affected.',
  explanation: 'Swapped outdoor stops for indoor ones keeping budget intact.',
  disruptions: [
    {
      id: 'dis-1',
      type: 'weather',
      severity: 'high',
      day_index: 2,
      summary: 'Rain 80%',
      source: 'Open-Meteo forecast',
    },
  ],
  cost_delta: -150,
  time_delta_min: 10,
  items_changed: 2,
  diff: [
    {
      op: 'replace',
      day: 2,
      stable_key: 'stb-tea-walk',
      before: {
        title: 'Happy Valley Tea Walk',
        start: '14:00',
        end: '16:00',
        cost: 500,
        setting: 'outdoor',
      },
      after: {
        title: 'Tibetan Craft Centre',
        start: '14:00',
        end: '16:00',
        cost: 350,
        setting: 'indoor',
      },
      why: 'Outdoor activity in rain',
    },
  ],
  created_at: new Date().toISOString(),
};

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

describe('ProposalSheet - Approve / Reject Flow', () => {
  it('renders reason, data source chip, impact row, and diff', () => {
    render(
      <ProposalSheet
        isOpen={true}
        onClose={vi.fn()}
        proposal={mockProposal}
        tripId="trip-test-01"
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/Rain expected Day 2/i)).toBeInTheDocument();
    expect(screen.getByText('Open-Meteo forecast')).toBeInTheDocument();
    expect(screen.getByText('-Rs 150')).toBeInTheDocument();
    expect(screen.getByText('+10m')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument(); // items changed
    expect(screen.getByText('Happy Valley Tea Walk')).toBeInTheDocument();
    expect(screen.getByText('Tibetan Craft Centre')).toBeInTheDocument();
  });

  it('triggers approve decision when user clicks Approve changes', async () => {
    const decideSpy = vi.spyOn(api, 'decideProposal').mockResolvedValue({
      status: 'approved',
      version_id: 'ver-trip-test-01-v2',
    });
    const onClose = vi.fn();

    render(
      <ProposalSheet
        isOpen={true}
        onClose={onClose}
        proposal={mockProposal}
        tripId="trip-test-01"
      />,
      { wrapper: createWrapper() }
    );

    const approveBtn = screen.getByRole('button', { name: /Approve changes/i });
    fireEvent.click(approveBtn);

    await waitFor(() => {
      expect(decideSpy).toHaveBeenCalledWith('prop-test-01', 'approve', undefined);
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('triggers reject decision when user clicks Reject', async () => {
    const decideSpy = vi.spyOn(api, 'decideProposal').mockResolvedValue({
      status: 'rejected',
    });
    const onClose = vi.fn();

    render(
      <ProposalSheet
        isOpen={true}
        onClose={onClose}
        proposal={mockProposal}
        tripId="trip-test-01"
      />,
      { wrapper: createWrapper() }
    );

    const rejectBtn = screen.getByRole('button', { name: /Reject/i });
    fireEvent.click(rejectBtn);

    await waitFor(() => {
      expect(decideSpy).toHaveBeenCalledWith('prop-test-01', 'reject', undefined);
      expect(onClose).toHaveBeenCalled();
    });
  });
});
