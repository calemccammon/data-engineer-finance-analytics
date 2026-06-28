// @ts-check
import { test, expect } from '@playwright/test';

const BASE = '/data-engineer-finance-analytics';

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
    // Icon SVGs have Tailwind size classes (w-4, w-5, etc.); chart SVGs do not
    await expect(page.locator('main svg:not([class*="w-"])').first()).toBeVisible({ timeout: 10000 });
  });

  test("renders today's snapshot table with data rows", async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    // Evidence DataTable briefly sets visibility:hidden during column measurement;
    // scrolling into view and allowing extra time lets it settle
    const table = page.locator('main table').first();
    await table.scrollIntoViewIfNeeded();
    await expect(table).toBeVisible({ timeout: 15000 });
    await expect(table.locator('tbody tr').first()).toBeVisible();
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
    await expect(page.locator('main svg:not([class*="w-"])').first()).toBeVisible({ timeout: 10000 });
  });

  test('renders rate regime bar chart and data table', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Rate Regime/i }).first()).toBeVisible();
    const table = page.locator('main table').first();
    await table.scrollIntoViewIfNeeded();
    await expect(table).toBeVisible({ timeout: 15000 });
    await expect(table.locator('tbody tr').first()).toBeVisible();
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
    await expect(page.locator('main svg:not([class*="w-"])').first()).toBeVisible({ timeout: 10000 });
  });

  test('renders monthly returns table with data rows', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Monthly Returns/i }).first()).toBeVisible();
    const table = page.locator('main table').first();
    await table.scrollIntoViewIfNeeded();
    await expect(table).toBeVisible({ timeout: 15000 });
    await expect(table.locator('tbody tr').first()).toBeVisible();
  });

  test('ticker dropdown changes displayed content', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    // Open Melt UI combobox, wait for listbox, select MSFT by text
    await page.locator('[role="combobox"]').first().click();
    await page.getByRole('listbox').waitFor({ timeout: 5000 });
    await page.getByRole('listbox').getByText('MSFT').click();
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[role="combobox"]').first()).toContainText('MSFT');
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




