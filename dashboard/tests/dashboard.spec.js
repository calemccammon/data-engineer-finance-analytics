// @ts-check
import { test, expect } from '@playwright/test';

const BASE = '/data-engineer-finance-analytics';

// Evidence runs SQL queries via DuckDB WASM in a Web Worker.
// This completes asynchronously *after* networkidle fires, so tests that
// depend on rendered data must wait for specific DOM signals rather than
// relying solely on networkidle.

// ── Home page ─────────────────────────────────────────────────────────────────

test.describe('Home page', () => {
  test('renders heading and summary metrics', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page.locator('text=Avg Daily Return %').first()).toBeVisible();
    await expect(page.locator('text=Gainers Today').first()).toBeVisible();
    await expect(page.locator('text=Losers Today').first()).toBeVisible();
    await expect(page.locator('text=Stocks Tracked').first()).toBeVisible();
  });

  test('renders 52-week performance chart', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /52-Week/i }).first()).toBeVisible();
    // SVG <text> elements (axis labels) only appear once DuckDB has rendered data
    await page.locator('main svg text').first().waitFor({ timeout: 30000 });
    expect(await page.locator('main svg text').count()).toBeGreaterThan(0);
  });

  test("renders today's snapshot table with data rows", async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    // Wait for tbody rows to be attached — Evidence DataTable keeps the <table>
    // visibility:hidden during column measurement; checking DOM attachment avoids that.
    await page.locator('main tbody tr').first().waitFor({ state: 'attached', timeout: 30000 });
    expect(await page.locator('main tbody tr').count()).toBeGreaterThan(0);
  });

  test('renders sector performance section', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Sector Performance/i }).first()).toBeVisible();
  });
});

// ── Macro page ────────────────────────────────────────────────────────────────

test.describe('Macro page', () => {
  test('renders heading and rate metric tiles', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page.locator('text=Fed Funds Rate').first()).toBeVisible();
    await expect(page.locator('text=10Y Treasury Yield').first()).toBeVisible();
    await expect(page.locator('text=Unemployment Rate').first()).toBeVisible();
  });

  test('renders interest rate chart', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Interest Rate/i }).first()).toBeVisible();
    await page.locator('main svg text').first().waitFor({ timeout: 30000 });
    expect(await page.locator('main svg text').count()).toBeGreaterThan(0);
  });

  test('renders rate regime bar chart and data table', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Rate Regime/i }).first()).toBeVisible();
    await page.locator('main tbody tr').first().waitFor({ state: 'attached', timeout: 30000 });
    expect(await page.locator('main tbody tr').count()).toBeGreaterThan(0);
  });
});

// ── Stocks page ───────────────────────────────────────────────────────────────

test.describe('Stocks page', () => {
  test('renders ticker dropdown defaulting to AAPL', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    const combobox = page.locator('[role="combobox"]').first();
    await expect(combobox).toBeVisible();
    await expect(combobox).toContainText('AAPL');
  });

  test('renders price history chart', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Price History/i }).first()).toBeVisible();
    await page.locator('main svg text').first().waitFor({ timeout: 30000 });
    expect(await page.locator('main svg text').count()).toBeGreaterThan(0);
  });

  test('renders monthly returns table with data rows', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Monthly Returns/i }).first()).toBeVisible();
    await page.locator('main tbody tr').first().waitFor({ state: 'attached', timeout: 30000 });
    expect(await page.locator('main tbody tr').count()).toBeGreaterThan(0);
  });
});

// ── Briefing page ─────────────────────────────────────────────────────────────

test.describe('Briefing page', () => {
  test('renders without error', async ({ page }) => {
    await page.goto(`${BASE}/briefing`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
    const content = page.locator('text=/briefing|market|No briefing/i').first();
    await expect(content).toBeVisible();
  });
});





