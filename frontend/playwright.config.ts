import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run start",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
      testIgnore: /a11y-axe\.spec\.ts/,
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
      testIgnore: /a11y-axe\.spec\.ts/,
    },
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 5"] },
      testIgnore: /a11y-axe\.spec\.ts/,
    },
  ],
});
