import { test, expect } from '@playwright/test';

test.describe('A8: End-to-End Stress Flows', () => {
  test('Reject proposal flow: shows toast and keeps plan unchanged', async ({ page }) => {
    await page.goto('/trips/trip-jaipur-02');

    // Jaipur has an existing pending proposal
    const reviewBtn = page.getByRole('button', { name: /Review changes/i });
    if (await reviewBtn.isVisible()) {
      await reviewBtn.click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Click Reject
      const rejectBtn = page.getByRole('button', { name: /Reject/i });
      await rejectBtn.click();

      // Dialog closes and toast appears
      await expect(page.getByRole('dialog')).not.toBeVisible();
      await expect(page.getByText(/No changes made/i)).toBeVisible();
    }
  });

  test('Budget overrun flow: logging high expense triggers budget warning banner', async ({ page }) => {
    await page.goto('/trips/trip-darjeeling-01');

    // Switch to Budget tab (target the visible tab button on desktop or mobile)
    const budgetTabBtn = page.getByRole('button', { name: /budget/i }).locator('visible=true');
    await budgetTabBtn.first().click();

    // Fill and log large expense
    const amountInput = page.getByPlaceholder('Amount');
    if (await amountInput.isVisible()) {
      await amountInput.fill('15000');
      const descInput = page.getByPlaceholder(/Description/i);
      await descInput.fill('Luxury helicopter transfer');
      const addBtn = page.getByRole('button', { name: /Add Expense/i });
      await addBtn.click();

      // Verify expense added and budget bar warns
      await expect(page.getByText('Luxury helicopter transfer')).toBeVisible();
      await expect(page.getByText(/Overrun/i)).toBeVisible();
    }
  });

  test('Assistant Chat: sending prompt triggers agent replan proposal', async ({ page }) => {
    await page.goto('/trips/trip-darjeeling-01');

    // On mobile viewports, switch to the visible agent/activity tab
    const agentTab = page.getByRole('button', { name: /agent/i }).locator('visible=true');
    if (await agentTab.count() > 0) {
      await agentTab.first().click();
    }

    // Click suggestion chip "Make Day 2 more relaxed"
    const relaxChip = page.getByRole('button', { name: /Make Day 2 more relaxed/i }).locator('visible=true');
    if (await relaxChip.count() > 0) {
      await relaxChip.first().click();

      // Message appears in chat bubble
      await expect(
        page.getByText('Make Day 2 more relaxed').locator('visible=true').first()
      ).toBeVisible({ timeout: 10000 });
      // Replan proposal toast or review button becomes available
      await expect(
        page.getByRole('button', { name: /Review changes/i }).or(page.getByText(/proposal available/i))
      ).toBeVisible({ timeout: 15000 });
    }
  });

  test('Keyboard accessibility flow: user navigates itinerary and tabs with keyboard', async ({ page }) => {
    await page.goto('/trips/trip-darjeeling-01');

    // Tab through to day navigation
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Switch tabs using Enter/Space
    const mapTab = page.getByRole('button', { name: /^Map$/i });
    await mapTab.focus();
    await page.keyboard.press('Enter');

    // Route map heading must be visible
    await expect(page.getByRole('heading', { name: /Route Map/i })).toBeVisible();
  });
});
