// @ts-check
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false, // single static server
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [['github'], ['html', { open: 'never' }]]
    : 'list',

  use: {
    baseURL: 'http://localhost:3000',
    navigationTimeout: 30_000,
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    // Python's built-in HTTP server — no npm package required.
    // Run `npm run build` (with EVIDENCE_BUILD_DIR=./build/data-engineer-finance-analytics)
    // before running these tests locally.
    command: 'python3 -m http.server 3000 --directory ./build',
    url: 'http://localhost:3000/data-engineer-finance-analytics/',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
