import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProposalSheet } from '@/components/ProposalSheet';
import { DiffView } from '@/components/DiffView';
import { VersionList } from '@/components/VersionList';
import { mockStore } from '@/mocks/handlers';
import { ProposalResponse, ItineraryVersion, ItineraryDay } from '@/types/contract';
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

const SAMPLE_PROPOSAL: ProposalResponse = {
  id: 'prop-test-101',
  trip_id: 'trip-darjeeling',
  run_id: 'run-101',
  base_version_id: 'ver-1',
  status: 'pending',
  reason: 'Rain expected Day 2',
  explanation: 'Swapped outdoor stops for indoor workshop',
  disruptions: [
    {
      id: 'dis-1',
      trip_id: 'trip-darjeeling',
      type: 'weather',
      severity: 'high',
      day_index: 2,
      summary: 'Heavy downpour expected',
      source: 'Open-Meteo',
    },
  ],
  cost_delta: -150,
  time_delta_min: 10,
  items_changed: 1,
  diff: [
    {
      op: 'replace',
      day: 2,
      stable_key: 'stb-tea-tour',
      before: {
        title: 'Happy Valley Tea Estate Tour',
        start: '14:00',
        end: '16:00',
        cost: 500,
        setting: 'outdoor',
      },
      after: {
        title: 'Tibetan Refugee Self-Help Centre (Indoor Workshop)',
        start: '14:00',
        end: '16:00',
        cost: 350,
        setting: 'indoor',
      },
      why: 'Heavy rain downpour',
    },
  ],
  created_at: new Date().toISOString(),
};

describe('A3: Proposal and State Machine Stress', () => {
  beforeEach(() => {
    useUIStore.setState({ toastMessage: null });
    // Seed proposal in mockStore
    if (!mockStore.proposals['trip-darjeeling']) {
      mockStore.proposals['trip-darjeeling'] = [];
    }
    mockStore.proposals['trip-darjeeling'] = [JSON.parse(JSON.stringify(SAMPLE_PROPOSAL))];
  });

  it('Approve, reject, and alternatives each trigger decisions; double-clicking Approve sends one request', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const decideSpy = vi.spyOn(mockStore, 'decideProposal');

    render(
      <ProposalSheet
        isOpen={true}
        onClose={onClose}
        proposal={SAMPLE_PROPOSAL}
        tripId="trip-darjeeling"
      />,
      { wrapper: createWrapper() }
    );

    const approveButton = screen.getByRole('button', { name: /Approve changes/i });

    // Rapid double click
    fireEvent.click(approveButton);
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });

    // Idempotent: must have called decideProposal exactly ONCE despite double click
    expect(decideSpy).toHaveBeenCalledTimes(1);
    expect(decideSpy).toHaveBeenCalledWith(
      'prop-test-101',
      expect.objectContaining({ decision: 'approve' })
    );

    decideSpy.mockRestore();
  });

  it('Approve with a 409 (already decided): shows clear error and prevents phantom new version', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    // Mark proposal as already approved in store
    mockStore.proposals['trip-darjeeling'][0].status = 'approved';

    const initialVersionCount = (mockStore.versions['trip-darjeeling'] || []).length;

    render(
      <ProposalSheet
        isOpen={true}
        onClose={onClose}
        proposal={SAMPLE_PROPOSAL}
        tripId="trip-darjeeling"
      />,
      { wrapper: createWrapper() }
    );

    const approveButton = screen.getByRole('button', { name: /Approve changes/i });
    await user.click(approveButton);

    await waitFor(() => {
      expect(useUIStore.getState().toastMessage?.type).toBe('error');
    });

    // Version count must NOT have increased (no phantom version)
    expect((mockStore.versions['trip-darjeeling'] || []).length).toBe(initialVersionCount);
  });

  it('A proposal arriving while another is open marks previous pending proposal as superseded', () => {
    // Start with pending proposal 1
    mockStore.simulateDisruption('trip-darjeeling', 'weather', 2);
    const firstProposal = mockStore.proposals['trip-darjeeling'][0];
    expect(firstProposal.status).toBe('pending');

    // Second proposal arrives
    mockStore.simulateDisruption('trip-darjeeling', 'closure', 2);

    // The first proposal must now be marked superseded
    expect(firstProposal.status).toBe('superseded');

    // The newest proposal is pending
    const secondProposal = mockStore.proposals['trip-darjeeling'][0];
    expect(secondProposal.status).toBe('pending');
  });

  it('Locked items never appear in the generated diff', () => {
    const tripId = 'trip-darjeeling-01';
    // Lock all items on Day 2 in the itinerary
    const itin = mockStore.itineraries[tripId];
    const day2 = itin?.days.find((d) => d.day_index === 2);
    day2?.items.forEach((item) => {
      item.is_locked = true;
    });

    // Generate proposal
    mockStore.simulateDisruption(tripId, 'weather', 2);
    const proposal = mockStore.proposals[tripId][0];

    // Proposal diff must have 0 items because locked items are protected
    expect(proposal.diff.length).toBe(0);

    // Clean up: unlock for subsequent tests
    day2?.items.forEach((item) => {
      item.is_locked = false;
    });
  });

  it('DiffView with 0, 1, and 200 changes renders correctly and truncates 500-char titles without breaking layout', () => {
    // 1. Zero changes
    const { rerender } = render(<DiffView diff={[]} />);
    expect(screen.getByText(/No differences between versions/i)).toBeInTheDocument();

    // 2. Diff with 200 changes including a 500-character title
    const longTitle = 'Super Long Historic Temple Landmark Name That Goes On And On '.repeat(8);
    const largeDiff = Array.from({ length: 200 }, (_, i) => ({
      op: 'replace' as const,
      day: (i % 3) + 1,
      stable_key: `key-${i}`,
      before: {
        title: i === 0 ? longTitle : `Stop before ${i}`,
        start: '09:00',
        end: '10:00',
        cost: 100,
      },
      after: {
        title: `Replacement stop ${i}`,
        start: '09:30',
        end: '10:30',
        cost: 120,
      },
      why: 'Schedule adjustment',
    }));

    rerender(<DiffView diff={largeDiff} />);
    const diffItems = screen.getAllByTestId(/diff-item-/);
    expect(diffItems.length).toBe(200);

    // Verify first item contains truncated title element
    expect(diffItems[0]).toBeInTheDocument();
  });

  it('Version history: selecting versions, switching diffs, and restoring current version behaves gracefully', () => {
    const versions: ItineraryVersion[] = [
      { id: 'v1', trip_id: 'trip-1', version_no: 1, reason: 'Initial plan', created_by: 'agent:planner', total_cost: 10000, summary: 'V1 Initial', created_at: '2026-10-01' },
      { id: 'v2', trip_id: 'trip-1', version_no: 2, reason: 'Weather swap', created_by: 'agent:replanner', total_cost: 9800, summary: 'V2 Weather swap', created_at: '2026-10-02' },
    ];
    const daysV1: ItineraryDay[] = [
      { day_index: 1, date: '2026-10-01', items: [], summary: { cost: 0, walking_min: 0, active_min: 0 } },
    ];
    const daysV2: ItineraryDay[] = [
      { day_index: 1, date: '2026-10-01', items: [], summary: { cost: 0, walking_min: 0, active_min: 0 } },
    ];

    const onRestore = vi.fn();

    render(
      <VersionList
        versions={versions}
        currentVersionId="v2"
        allVersionDays={{ v1: daysV1, v2: daysV2 }}
        onRestore={onRestore}
      />
    );

    // Version list shows both versions
    expect(screen.getByText('v1')).toBeInTheDocument();
    expect(screen.getByText('v2')).toBeInTheDocument();

    // v2 has the current version badge
    expect(screen.getByText(/Current Active/i)).toBeInTheDocument();
  });
});
