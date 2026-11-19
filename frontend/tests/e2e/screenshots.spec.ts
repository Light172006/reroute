import { test, Page } from '@playwright/test';
import fs from 'fs';
import path from 'path';

test.describe('Visual Screenshots Capture', () => {
  test.beforeAll(() => {
    const dir = path.resolve(process.cwd(), 'screenshots');
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });

  const setMode = async (page: Page, mode: 'light' | 'dark') => {
    await page.evaluate((themeMode: string) => {
      document.documentElement.classList.remove('light', 'dark');
      document.documentElement.classList.add(themeMode);
      localStorage.setItem('theme', themeMode);
    }, mode);
    await page.waitForTimeout(300);
  };

  test('Capture screenshots across key flows (light & dark)', async ({ page }) => {
    test.setTimeout(90000);
    await page.setViewportSize({ width: 1440, height: 900 });

    // 1. Landing Page
    await page.goto('/');
    await page.waitForTimeout(400);
    await setMode(page, 'light');
    await page.screenshot({ path: 'screenshots/01-landing-light.png' });

    await setMode(page, 'dark');
    await page.screenshot({ path: 'screenshots/01-landing-dark.png' });

    // 2. Trips List Page
    await page.goto('/trips');
    await page.waitForTimeout(400);
    await setMode(page, 'light');
    await page.screenshot({ path: 'screenshots/02-trips-list-light.png' });

    await setMode(page, 'dark');
    await page.screenshot({ path: 'screenshots/02-trips-list-dark.png' });

    // 3. Workspace with Disruption Banner
    await page.goto('/trips/trip-darjeeling-01');
    await page.waitForTimeout(600);

    // Simulate disruption if not already pending
    const simButton = page.getByRole('button', { name: /Simulate disruption/i });
    if (await simButton.isVisible()) {
      await simButton.click();
      await page.getByRole('menuitem', { name: /Rain on Day 2/i }).click();
      await page.waitForTimeout(800);
    }

    await setMode(page, 'light');
    await page.screenshot({ path: 'screenshots/03-workspace-banner-light.png' });

    await setMode(page, 'dark');
    await page.screenshot({ path: 'screenshots/03-workspace-banner-dark.png' });

    // 4. Proposal Review Modal / Sheet
    const reviewBtn = page.getByRole('button', { name: /Review changes/i });
    if (await reviewBtn.isVisible()) {
      await reviewBtn.click();
      await page.waitForTimeout(600);

      await setMode(page, 'light');
      await page.screenshot({ path: 'screenshots/04-proposal-review-light.png' });

      await setMode(page, 'dark');
      await page.screenshot({ path: 'screenshots/04-proposal-review-dark.png' });

      // Close modal by pressing Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }

    // 5. Map Tab
    const mapTab = page.getByRole('button', { name: /^map$/i }).first();
    await mapTab.click();
    await page.waitForTimeout(800);

    await setMode(page, 'light');
    await page.screenshot({ path: 'screenshots/05-map-tab-light.png' });

    await setMode(page, 'dark');
    await page.screenshot({ path: 'screenshots/05-map-tab-dark.png' });

    // 6. Budget Tab
    const budgetTab = page.getByRole('button', { name: /^budget$/i }).first();
    await budgetTab.click();
    await page.waitForTimeout(800);

    await setMode(page, 'light');
    await page.screenshot({ path: 'screenshots/06-budget-tab-light.png' });

    await setMode(page, 'dark');
    await page.screenshot({ path: 'screenshots/06-budget-tab-dark.png' });

    // 7. Styleguide
    await page.goto('/dev/styleguide');
    await page.waitForTimeout(800);

    await setMode(page, 'light');
    await page.screenshot({ path: 'screenshots/07-styleguide-light.png' });

    await setMode(page, 'dark');
    await page.screenshot({ path: 'screenshots/07-styleguide-dark.png' });

    // 8. Mobile 360px Dark Mode Checks
    await page.setViewportSize({ width: 360, height: 780 });

    // 8a. Landing (360px dark)
    await page.goto('/');
    await page.waitForTimeout(400);
    await setMode(page, 'dark');
    await page.screenshot({ path: 'screenshots/01-landing-dark-360px.png' });

    // 8b. Trips List (360px dark)
    await page.goto('/trips');
    await page.waitForTimeout(400);
    await setMode(page, 'dark');
    await page.screenshot({ path: 'screenshots/02-trips-list-dark-360px.png' });

    // 8c. Workspace (360px dark)
    await page.goto('/trips/trip-darjeeling-01');
    await page.waitForTimeout(600);
    await setMode(page, 'dark');
    await page.screenshot({ path: 'screenshots/03-workspace-banner-dark-360px.png' });

    // 8d. Proposal Review (360px dark)
    const mobileReviewBtn = page.getByRole('button', { name: /Review changes/i });
    if (await mobileReviewBtn.isVisible()) {
      await mobileReviewBtn.click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: 'screenshots/04-proposal-review-dark-360px.png' });
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }

    // 8e. Map Tab (360px dark)
    const mobileMapTab = page.getByRole('button', { name: /^map$/i }).first();
    if (await mobileMapTab.isVisible()) {
      await mobileMapTab.click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: 'screenshots/05-map-tab-dark-360px.png' });
    }

    // 8f. Budget Tab (360px dark)
    const mobileBudgetTab = page.getByRole('button', { name: /^budget$/i }).first();
    if (await mobileBudgetTab.isVisible()) {
      await mobileBudgetTab.click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: 'screenshots/06-budget-tab-dark-360px.png' });
    }

    // 8g. Styleguide (360px dark)
    await page.goto('/dev/styleguide');
    await page.waitForTimeout(600);
    await setMode(page, 'dark');
    await page.screenshot({ path: 'screenshots/07-styleguide-dark-360px.png' });
  });
});
