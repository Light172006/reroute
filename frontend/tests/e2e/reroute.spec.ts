import { test, expect } from '@playwright/test';

test.describe('Reroute E2E Flows', () => {
  test('Flow 1: Create trip -> generate -> view itinerary', async ({ page }) => {
    // 1. Visit new trip wizard
    await page.goto('/trips/new');

    // Step 1: Where & when
    await expect(page.getByText('Where and when are you traveling?')).toBeVisible();
    await page.getByPlaceholder(/Darjeeling, Jaipur/i).fill('Darjeeling');
    await page.getByRole('button', { name: /Next: Budget/i }).click();

    // Step 2: Budget
    await expect(page.getByText('What is your budget?')).toBeVisible();
    await page.getByRole('button', { name: /Next: Vibe/i }).click();

    // Step 3: Vibe & Pace
    await expect(page.getByText(/Vibe, Pace & Special Preferences/i)).toBeVisible();
    await page.getByRole('button', { name: /Generate My Trip/i }).click();

    // 2. Expect redirection to workspace
    await expect(page).toHaveURL(/.*\/trips\/.*/);

    // 3. Verify itinerary renders with day navigation and items (after generation completes)
    await expect(page.getByText(/Batasia Loop & War Memorial/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/Chowrasta Mall Road Stroll/i)).toBeVisible();
    // On desktop, Budget Tracker is in the left sidebar; on mobile, verify day navigation / tabs are visible
    const budgetTracker = page.getByText(/Budget Tracker/i);
    if (await budgetTracker.isVisible()) {
      await expect(budgetTracker).toBeVisible();
    } else {
      await expect(page.getByRole('button', { name: /budget/i }).first()).toBeVisible();
    }
  });

  test('Flow 2: Simulate rain -> review proposal -> approve -> new version appears', async ({ page }) => {
    // 1. Visit existing Darjeeling trip workspace
    await page.goto('/trips/trip-darjeeling-01');

    // 2. Open simulate disruption dropdown
    const simButton = page.getByRole('button', { name: /Simulate disruption/i });
    await expect(simButton).toBeVisible();
    await simButton.click();

    // 3. Click Rain on Day 2
    const rainOption = page.getByRole('menuitem', { name: /Rain on Day 2/i });
    await expect(rainOption).toBeVisible();
    await rainOption.click();

    // 4. Expect disruption banner to appear with "Review changes"
    const reviewBtn = page.getByRole('button', { name: /Review changes/i });
    await expect(reviewBtn).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('alert').filter({ hasText: /Rain expected Day 2/i })).toBeVisible();

    // 5. Click Review changes -> opens modal/sheet
    await reviewBtn.click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText(/Review Itinerary Changes/i)).toBeVisible();
    await expect(page.getByText(/Detailed Comparison/i)).toBeVisible();
    await expect(page.getByText(/Happy Valley Tea Estate Tour/i)).toBeVisible();
    await expect(page.getByText(/Tibetan Refugee Self-Help Centre/i)).toBeVisible();

    // 6. Click Approve changes
    const approveBtn = page.getByRole('button', { name: /Approve changes/i });
    await approveBtn.click();

    // 7. Verify Toast and updated version badge
    await expect(page.getByText(/Done. Itinerary updated/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('link', { name: /v2/i })).toBeVisible({ timeout: 5000 });
  });
});
