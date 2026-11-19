import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { formatDateRange, formatCurrency, formatDeltaCurrency } from '@/lib/format';
import { BudgetBar } from '@/components/BudgetBar';
import { ItineraryItemCard } from '@/components/ItineraryItemCard';
import { TravelConnector } from '@/components/TravelConnector';
import { ItineraryItem, BudgetSummary } from '@/types/contract';

describe('A4: Data and Edge-Case Stress', () => {
  describe('Dates and Timezone handling', () => {
    it('Single-day trip formats without range separator', () => {
      const formatted = formatDateRange('2026-10-15', '2026-10-15');
      expect(formatted).toBe('Oct 15, 2026');
    });

    it('Trip spanning year boundary includes both years', () => {
      const formatted = formatDateRange('2026-12-28', '2027-01-04');
      expect(formatted).toBe('Dec 28, 2026 - Jan 4, 2027');
    });

    it('Trip spanning months in same year formats cleanly', () => {
      const formatted = formatDateRange('2026-04-28', '2026-05-03');
      expect(formatted).toBe('Apr 28 - May 3, 2026');
    });

    it('Trip within same month formats cleanly', () => {
      const formatted = formatDateRange('2026-06-10', '2026-06-15');
      expect(formatted).toBe('Jun 10 - 15, 2026');
    });
  });

  describe('Budget boundaries and currency formatting', () => {
    it('Formats 0, negative amounts, large numbers (1e9), and decimals', () => {
      expect(formatCurrency(0, 'INR')).toBe('Rs 0');
      expect(formatCurrency(-500, 'INR')).toBe('Rs -500');
      expect(formatCurrency(1e9, 'INR')).toBe('Rs 1,00,00,00,000');
      expect(formatCurrency(1250.75, 'INR')).toBe('Rs 1,251');

      expect(formatDeltaCurrency(-150, 'INR')).toBe('-Rs 150');
      expect(formatDeltaCurrency(200, 'INR')).toBe('+Rs 200');
      expect(formatDeltaCurrency(0, 'INR')).toBe('Rs 0');
    });

    it('BudgetBar: handles overrun boundaries: 9.99% (no warning), 10.0% (warning), and 100%+ (danger)', () => {
      // 1. Overrun at 9.99% -> No warning
      const budget999: BudgetSummary = {
        planned_total: 10000,
        actual_total: 10999,
        remaining: 0,
        by_category: [],
        overrun_pct: 9.99,
      };
      const { rerender } = render(<BudgetBar budget={budget999} />);
      expect(screen.queryByText(/Overrun by/i)).toBeNull();

      // 2. Overrun at exactly 10.0% -> Shows warning
      const budget10: BudgetSummary = {
        planned_total: 10000,
        actual_total: 11000,
        remaining: 0,
        by_category: [],
        overrun_pct: 10.0,
      };
      rerender(<BudgetBar budget={budget10} />);
      expect(screen.getByText(/Overrun by 10%/i)).toBeInTheDocument();

      // 3. Overrun at 120%
      const budget120: BudgetSummary = {
        planned_total: 10000,
        actual_total: 22000,
        remaining: 0,
        by_category: [],
        overrun_pct: 120,
      };
      rerender(<BudgetBar budget={budget120} />);
      expect(screen.getByText(/Overrun by 120%/i)).toBeInTheDocument();
    });

    it('BudgetBar: handles planned_total 0 and negative actuals gracefully without NaN or negative width', () => {
      const budgetZero: BudgetSummary = {
        planned_total: 0,
        actual_total: 500,
        remaining: 0,
        by_category: [],
        overrun_pct: 100,
      };
      const { rerender } = render(<BudgetBar budget={budgetZero} />);
      const progress = screen.getByRole('progressbar');
      expect(progress.getAttribute('aria-valuenow')).toBe('100');

      const budgetNegative: BudgetSummary = {
        planned_total: 5000,
        actual_total: -200,
        remaining: 5200,
        by_category: [],
        overrun_pct: 0,
      };
      rerender(<BudgetBar budget={budgetNegative} />);
      const progressNeg = screen.getByRole('progressbar');
      expect(progressNeg.getAttribute('aria-valuenow')).toBe('0');
    });
  });

  describe('Edge-case text strings and XSS protection', () => {
    it('Renders HTML tags, <script> and combining characters as raw text without execution', () => {
      const xssItem: ItineraryItem = {
        id: 'item-xss',
        stable_key: 'stb-xss',
        position: 0,
        title: '<script>alert("xss")</script><img src=x onerror=alert(1)> Special & "Quotes"',
        category: 'sightseeing',
        setting: 'indoor',
        start_time: '10:00',
        end_time: '11:00',
        est_cost: 0,
        is_locked: false,
        flags: [],
        notes: '<strong>Note</strong> text with RTL: سلام and combining chars: Ẑa̋l̋g̋ő',
      };

      render(
        <ItineraryItemCard
          item={xssItem}
          onToggleLock={vi.fn()}
          onDelete={vi.fn()}
        />
      );

      // Raw script text is rendered as text content, not executed as DOM elements
      expect(screen.getByText(/<script>alert\("xss"\)<\/script>/i)).toBeInTheDocument();
      expect(screen.getByText(/Ẑa̋l̋g̋ő/i)).toBeInTheDocument();
      expect(document.querySelector('script:not([src])')).toBeNull();
    });

    it('500-character titles render cleanly with truncation', () => {
      const hugeTitle = 'A'.repeat(500);
      const longItem: ItineraryItem = {
        id: 'item-long',
        stable_key: 'stb-long',
        position: 0,
        title: hugeTitle,
        category: 'sightseeing',
        setting: 'indoor',
        start_time: '10:00',
        end_time: '11:00',
        est_cost: 100,
        is_locked: false,
        flags: [],
      };

      render(
        <ItineraryItemCard
          item={longItem}
          onToggleLock={vi.fn()}
          onDelete={vi.fn()}
        />
      );

      expect(screen.getByText(hugeTitle)).toBeInTheDocument();
    });
  });

  describe('Missing and null fields handling', () => {
    it('ItineraryItemCard: handles null notes, null lat/lng, and empty flags without crashing', () => {
      const nullItem: ItineraryItem = {
        id: 'item-nulls',
        stable_key: 'stb-nulls',
        position: 0,
        title: 'Minimal Stop',
        category: 'sightseeing',
        setting: 'indoor',
        start_time: '12:00',
        end_time: '13:00',
        est_cost: 0,
        lat: null,
        lng: null,
        place_id: null,
        travel: null,
        notes: null,
        is_locked: false,
        flags: [],
      };

      render(
        <ItineraryItemCard
          item={nullItem}
          onToggleLock={vi.fn()}
          onDelete={vi.fn()}
        />
      );

      expect(screen.getByText('Minimal Stop')).toBeInTheDocument();
    });

    it('TravelConnector: handles null travel info gracefully by rendering a dashed connector', () => {
      const { container } = render(<TravelConnector travel={null} />);
      expect(container.firstChild).toBeInTheDocument();
      expect(container.firstChild).toHaveClass('border-dashed');
    });
  });
});
