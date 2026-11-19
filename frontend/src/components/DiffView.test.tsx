import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DiffView } from './DiffView';
import { ProposalDiffItem } from '@/types/contract';

describe('DiffView', () => {
  it('renders empty message when diff is empty', () => {
    render(<DiffView diff={[]} />);
    expect(screen.getByText(/no differences between versions/i)).toBeInTheDocument();
  });

  it('renders removed and added items with proper labels and icons', () => {
    const mockDiff: ProposalDiffItem[] = [
      {
        op: 'replace',
        day: 2,
        stable_key: 'stb-happy-valley',
        before: {
          title: 'Happy Valley Tea Estate Tour',
          start: '14:00',
          end: '16:00',
          cost: 500,
          setting: 'outdoor',
        },
        after: {
          title: 'Tibetan Refugee Self-Help Centre',
          start: '14:00',
          end: '16:00',
          cost: 200,
          setting: 'indoor',
        },
        why: 'Heavy rain forecasted during afternoon',
      },
    ];

    render(<DiffView diff={mockDiff} currency="INR" />);

    // Day badge
    expect(screen.getByText('Day 2')).toBeInTheDocument();

    // Reason
    expect(screen.getByText(/Heavy rain forecasted during afternoon/i)).toBeInTheDocument();

    // Removed section
    expect(screen.getByText('Removed stop')).toBeInTheDocument();
    expect(screen.getByText('Happy Valley Tea Estate Tour')).toBeInTheDocument();
    expect(screen.getByText('Rs 500')).toBeInTheDocument();

    // Added section
    expect(screen.getByText('Proposed replacement')).toBeInTheDocument();
    expect(screen.getByText('Tibetan Refugee Self-Help Centre')).toBeInTheDocument();
    expect(screen.getByText('Rs 200')).toBeInTheDocument();
    expect(screen.getByText(/Setting:/i)).toBeInTheDocument();
  });

  it('indicates when a stop is locked', () => {
    const mockDiff: ProposalDiffItem[] = [
      {
        op: 'replace',
        day: 1,
        stable_key: 'stb-zoo',
        before: {
          title: 'Himalayan Zoo',
          start: '10:00',
          end: '12:00',
          cost: 200,
          is_locked: true,
        },
        after: {
          title: 'Museum',
          start: '10:00',
          end: '12:00',
          cost: 150,
        },
      },
    ];

    render(<DiffView diff={mockDiff} />);
    expect(screen.getByText('Item is locked')).toBeInTheDocument();
  });
});
