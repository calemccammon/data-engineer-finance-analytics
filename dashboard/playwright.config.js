// @ts-check
import { defineConfig, devices } from '@playwright/test';

// When PLAYWRIGHT_BASE_URL is set (e.g. the deployed GitHub Pages URL), tests
// run directly against that live site with no local server needed.
// Otherwise, a local Python HTTP server is started for development/local runs.
const liveBaseUrl = process.env.PLAYWRIGHT_BASE_URL;

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [['github'], ['html', { open: 'never' }]]
    : 'list',

  use: {
    baseURL: liveBaseUrl ?? 'http://localhost:3000',
    navigationTimeout: 30_000,
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Only spin up a local server when not testing against a live URL.
  // For local dev: run `npm run build` first, then `npm run test:e2e`.
  webServer: liveBaseUrl
    ? undefined
    : {
        command: 'python3 -m http.server 3000 --directory ./build',
        url: 'http://localhost:3000/data-engineer-finance-analytics/',
        reuseExistingServer: true,
        timeout: 30_000,
      },
});
