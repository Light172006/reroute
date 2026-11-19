import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const ROUTES = [
  '/',
  '/login',
  '/signup',
  '/trips',
  '/trips/new',
  '/trips/trip-darjeeling-01',
  '/trips/trip-darjeeling-01/versions',
  '/settings',
];

test.describe('A5: Accessibility Audit with Axe', () => {
  for (const route of ROUTES) {
    test(`Route ${route} has zero serious or critical axe violations in light theme`, async ({ page }) => {
      await page.goto(route);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(400);

      // Set light theme
      await page.evaluate(() => {
        document.documentElement.classList.remove('dark');
      });
      await page.waitForTimeout(200);

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();

      const seriousOrCritical = results.violations.filter(
        (v) => v.impact === 'serious' || v.impact === 'critical'
      );

      expect(seriousOrCritical).toEqual([]);
    });

    test(`Route ${route} has zero serious or critical axe violations in dark theme`, async ({ page }) => {
      await page.goto(route);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(400);

      // Set dark theme
      await page.evaluate(() => {
        document.documentElement.classList.add('dark');
      });
      await page.waitForTimeout(200);

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();

      const seriousOrCritical = results.violations.filter(
        (v) => v.impact === 'serious' || v.impact === 'critical'
      );

      expect(seriousOrCritical).toEqual([]);
    });
  }
});
