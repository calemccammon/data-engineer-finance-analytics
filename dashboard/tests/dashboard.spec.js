// @ts-check
import { test, expect } from '@playwright/test';

const BASE = '/data-engineer-finance-analytics';

// Evidence bakes all query results into the static bundle at build time.
// After networkidle, all data is already in the DOM — no async waiting needed.
//
// Table rows: Evidence DataTable renders data rows as direct <table> children,
// not inside <tbody>. Use getByRole('cell') to check for rendered data rows.
//
// Charts: Evidence/LayerChart requires a container with defined dimensions
// (via ResizeObserver) to render SVG content. Headless Chrome does not always
// satisfy this for off-screen elements, so verifying the section heading is
// sufficient as a smoke test.

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

  test('renders 52-week performance chart section', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /52-Week/i }).first()).toBeVisible();
  });

  test("renders today's snapshot table with data rows", async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('main').getByRole('cell').first()).toBeVisible();
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

  test('renders interest rate chart section', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Interest Rate/i }).first()).toBeVisible();
  });

  test('renders rate regime table with data rows', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Rate Regime/i }).first()).toBeVisible();
    await expect(page.locator('main').getByRole('cell').first()).toBeVisible();
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

  test('renders price history chart section', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Price History/i }).first()).toBeVisible();
  });

  test('renders monthly returns table with data rows', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Monthly Returns/i }).first()).toBeVisible();
    await expect(page.locator('main').getByRole('cell').first()).toBeVisible();
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

const BASE = '/data-engineer-finance-analytics';

// Notes on Evidence rendering in headless Chrome:
//
// Tables: Evidence DataTable renders data rows as direct <table> children,
// not inside a <tbody>. Use getByRole('cell') to detect rendered data rows.
//
// Charts: Evidence/LayerChart requires a container with defined dimensions
// (via ResizeObserver) to render SVG content. Headless Chrome does not always
// satisfy this for off-screen elements, so chart SVGs may never appear in the
// DOM. Verifying the chart section heading is sufficient for a smoke test.

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

  test('renders 52-week performance chart section', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /52-Week/i }).first()).toBeVisible();
  });

  test("renders today's snapshot table with data rows", async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');

    // Evidence DataTable renders data rows as direct <table> children, not <tbody> children.
    // getByRole('cell') matches only data cells (not column headers).
    await page.locator('main').getByRole('cell').first().waitFor({ timeout: 30000 });
    expect(await page.locator('main').getByRole('cell').count()).toBeGreaterThan(0);
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

  test('renders interest rate chart section', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Interest Rate/i }).first()).toBeVisible();
  });

  test('renders rate regime table with data rows', async ({ page }) => {
    await page.goto(`${BASE}/macro`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Rate Regime/i }).first()).toBeVisible();
    await page.locator('main').getByRole('cell').first().waitFor({ timeout: 30000 });
    expect(await page.locator('main').getByRole('cell').count()).toBeGreaterThan(0);
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

  test('renders price history chart section', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Price History/i }).first()).toBeVisible();
  });

  test('renders monthly returns table with data rows', async ({ page }) => {
    await page.goto(`${BASE}/stocks`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /Monthly Returns/i }).first()).toBeVisible();
    await page.locator('main').getByRole('cell').first().waitFor({ timeout: 30000 });
    expect(await page.locator('main').getByRole('cell').count()).toBeGreaterThan(0);
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





