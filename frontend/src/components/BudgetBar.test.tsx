import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BudgetBar } from './BudgetBar';
import { BudgetSummary } from '@/types/contract';

describe('BudgetBar & Overrun Calculation', () => {
  it('renders normal progress when within budget', () => {
    const budget: BudgetSummary = {
      planned_total: 10000,
      actual_total: 6000,
      remaining: 4000,
      by_category: [],
      overrun_pct: 0,
    };

    render(<BudgetBar budget={budget} currency="INR" />);

    expect(screen.getByText('Budget Tracker')).toBeInTheDocument();
    expect(screen.getByText('Rs 6,000 / Rs 10,000')).toBeInTheDocument();
    expect(screen.queryByText(/Overrun by/i)).not.toBeInTheDocument();

    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '60');
  });

  it('detects and displays warning when actual exceeds planned by 10%+', () => {
    const onReduceCost = vi.fn();
    const budget: BudgetSummary = {
      planned_total: 10000,
      actual_total: 11500,
      remaining: 0,
      by_category: [],
      overrun_pct: 15, // 15% overrun
    };

    render(<BudgetBar budget={budget} currency="INR" onReduceCost={onReduceCost} />);

    // Overrun text
    expect(screen.getByText('Overrun by 15%')).toBeInTheDocument();

    // Reduce cost action
    const reduceBtn = screen.getByText('Reduce cost');
    expect(reduceBtn).toBeInTheDocument();

    fireEvent.click(reduceBtn);
    expect(onReduceCost).toHaveBeenCalledTimes(1);
  });
});
