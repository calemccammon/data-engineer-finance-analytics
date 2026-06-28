// @ts-check
import { test, expect } from '@playwright/test';

const BASE = '/data-engineer-finance-analytics';

// ── Home page ─────────────────────────────────────────────────────────────────

test.describe('Home page', () => {
  test('renders heading and summary metrics', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('h1')).toBeVisible();
    // Four BigValue metric tiles should be present
    await expect(page.locator('text=Avg Daily Return %')).toBeVisible();
    await expect(page.locator('text=Gainers Today')).toBeVisible();
    await expect(page.locator('text=Losers Today')).toBeVisible();
    await expect(page.locator('text=Stocks Tracked')).toBeVisible();
  });

  test('renders 52-week performance chart', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=52-Week Return by Ticker')).toBeVisible();
    await expect(page.locator('svg').first()).toBeVisible();
  });

  test("renders today's snapshot table with data rows", async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    const table = page.locator('table').first();
    await expect(table).toBeVisible();
    const rows = table.locator('tbody tr');
    await expect(rows).not.toHaveCount(0);
  });

  test('renders sector performance section', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Sector Performance')).toBeVisible();
  });
});

// ── Macro page ────────────────────────────────────────────────────────────────

test.describe('Macro page', () => {
  test('renders heading and rate metric tiles', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('text=Fed Funds Rate')).toBeVisible();
    await expect(page.locator('text=10Y Treasury Yield')).toBeVisible();
    await expect(page.locator('text=Unemployment Rate')).toBeVisible();
  });

  test('renders interest rate chart', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Interest Rate Environment')).toBeVisible();
    await expect(page.locator('svg').first()).toBeVisible();
  });

  test('renders rate regime bar chart and data table', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Stock Returns by Rate Regime')).toBeVisible();
    const table = page.locator('table').first();
    await expect(table).toBeVisible();
    const rows = table.locator('tbody tr');
    await expect(rows).not.toHaveCount(0);
  });
});

// ── Stocks page ───────────────────────────────────────────────────────────────

test.describe('Stocks page', () => {
  test('renders ticker dropdown defaulting to AAPL', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=AAPL')).toBeVisible();
  });

  test('renders price history chart', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Price History')).toBeVisible();
    await expect(page.locator('svg').first()).toBeVisible();
  });

  test('renders monthly returns table with data rows', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Monthly Returns')).toBeVisible();
    const table = page.locator('table').first();
    await expect(table).toBeVisible();
    const rows = table.locator('tbody tr');
    await expect(rows).not.toHaveCount(0);
  });

  test('ticker dropdown changes displayed content', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    // Change ticker and verify the heading updates
    const dropdown = page.locator('select, [role="combobox"]').first();
    await dropdown.selectOption('MSFT');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=MSFT')).toBeVisible();
  });
});

// ── Briefing page ─────────────────────────────────────────────────────────────

test.describe('Briefing page', () => {
  test('renders without error', async ({ page }) => {
    await page.goto(`${BASE}/briefing`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();
    // Either a briefing or the "not generated yet" placeholder should be present
    const content = page.locator('text=/briefing|market|No briefing/i').first();
    await expect(content).toBeVisible();
  });
});

