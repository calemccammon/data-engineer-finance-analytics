"""Generate an AI market briefing using Gemini and write it to the Evidence dashboard.

Queries market and macro data from the active warehouse (DuckDB or BigQuery),
sends a structured prompt to the Gemini API, and writes the response to
dashboard/pages/briefing.md so Evidence renders it as a static page.

Usage:
    python generate_briefing.py              # Uses TARGET from .env
    python generate_briefing.py --dry-run   # Print prompt + response, don't write file
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent
OUTPUT_PATH = PROJECT_ROOT / "dashboard" / "pages" / "briefing.md"
TARGET = os.environ.get("TARGET", "local")


# ── Data fetching ─────────────────────────────────────────────────────────────

def _fetch_from_duckdb() -> dict:
    """Fetch market metrics from the local DuckDB file."""
    import duckdb
    db_path = os.environ.get(
        "FINANCE_DB_PATH",
        str(PROJECT_ROOT / "data" / "processed" / "finance.duckdb"),
    )
    con = duckdb.connect(db_path, read_only=True)
    try:
        return _run_queries(con)
    finally:
        con.close()


def _fetch_from_bigquery() -> dict:
    """Fetch market metrics from BigQuery."""
    from google.cloud import bigquery
    from google.oauth2 import service_account

    project = os.environ["BQ_PROJECT"]
    keyfile = os.environ.get("BQ_KEYFILE") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if keyfile and Path(keyfile).exists():
        creds = service_account.Credentials.from_service_account_file(
            keyfile,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        client = bigquery.Client(project=project, credentials=creds)
    else:
        client = bigquery.Client(project=project)

    dataset = "finance_marts"

    class BQAdapter:
        """Thin wrapper so _run_queries works with both DuckDB and BQ connections."""
        def __init__(self, bq_client, bq_dataset):
            self._client = bq_client
            self._dataset = bq_dataset

        def execute(self, sql):
            # Rewrite unqualified table refs to fully-qualified BQ refs
            sql = sql.replace(
                "main_marts.fct_daily_trading",
                f"`{project}.{self._dataset}.fct_daily_trading`",
            )
            return self._client.query(sql).result()

        def fetchall(self, result):
            return [dict(row) for row in result]

    adapter = BQAdapter(client, dataset)
    return _run_queries(adapter, bigquery=True)


def _run_queries(con, bigquery: bool = False) -> dict:
    """Run all metric queries and return a structured dict."""

    def q(sql):
        if bigquery:
            result = con.execute(sql)
            return con.fetchall(result)
        else:
            cursor = con.execute(sql)
            columns = [d[0] for d in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    # Latest date
    as_of = q("""
        SELECT MAX(trading_date) AS as_of_date
        FROM main_marts.fct_daily_trading
    """)[0]["as_of_date"]

    # Daily snapshot — all tickers (exclude first-day rows where return is NULL)
    daily = q("""
        SELECT
            ticker,
            company_name,
            sector,
            ROUND(close_price, 2)              AS close_price,
            ROUND(daily_return_pct, 3)          AS daily_return_pct,
            ROUND(volatility_20d_annualized, 1) AS vol_20d_pct,
            ROUND(close_price / NULLIF(sma_200d, 0) - 1, 3) AS pct_vs_200sma,
            ROUND(price_position_52w * 100, 1)  AS position_52w_pct
        FROM main_marts.fct_daily_trading
        WHERE trading_date = (SELECT MAX(trading_date) FROM main_marts.fct_daily_trading)
          AND daily_return_pct IS NOT NULL
        ORDER BY daily_return_pct DESC
    """)

    # 52-week performance
    performance_52w = q("""
        SELECT
            ticker,
            company_name,
            ROUND(
                (LAST_VALUE(close_price) OVER (PARTITION BY ticker ORDER BY trading_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
                 / FIRST_VALUE(close_price) OVER (PARTITION BY ticker ORDER BY trading_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) - 1) * 100,
                1
            ) AS return_52w_pct
        FROM main_marts.fct_daily_trading
        WHERE trading_date >= (
            SELECT MAX(trading_date) - 365
            FROM main_marts.fct_daily_trading
        )
        QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY trading_date DESC) = 1
        ORDER BY return_52w_pct DESC
    """)

    # Macro indicators
    macro = q("""
        SELECT
            ROUND(fed_funds_rate, 2)           AS fed_funds_rate,
            ROUND(treasury_yield_10y, 2)        AS treasury_yield_10y,
            ROUND(real_yield_10y, 2)            AS real_yield_10y,
            ROUND(unemployment_rate, 1)         AS unemployment_rate,
            ROUND(breakeven_inflation_10y, 2)   AS breakeven_inflation_10y,
            ROUND(gdp_growth_rate, 1)           AS gdp_growth_rate
        FROM main_marts.fct_daily_trading
        WHERE ticker = 'AAPL'
          AND trading_date = (SELECT MAX(trading_date) FROM main_marts.fct_daily_trading)
    """)[0]

    # Sector summary
    sectors = q("""
        SELECT
            sector,
            ROUND(AVG(daily_return_pct), 3) AS avg_return,
            ROUND(AVG(volatility_20d_annualized), 1) AS avg_vol
        FROM main_marts.fct_daily_trading
        WHERE trading_date = (SELECT MAX(trading_date) FROM main_marts.fct_daily_trading)
        GROUP BY sector
        ORDER BY avg_return DESC
    """)

    return {
        "as_of_date": str(as_of),
        "daily": daily,
        "performance_52w": performance_52w,
        "macro": macro,
        "sectors": sectors,
    }


# ── Prompt construction ───────────────────────────────────────────────────────

def _build_prompt(data: dict) -> str:
    daily = data["daily"]
    macro = data["macro"]
    sectors = data["sectors"]
    perf = data["performance_52w"]

    gainers = [d for d in daily if d["daily_return_pct"] > 0]
    losers  = [d for d in daily if d["daily_return_pct"] < 0]
    top_gainer = max(daily, key=lambda x: x["daily_return_pct"])
    top_loser  = min(daily, key=lambda x: x["daily_return_pct"])
    best_52w   = max(perf, key=lambda x: x["return_52w_pct"])
    worst_52w  = min(perf, key=lambda x: x["return_52w_pct"])

    sector_lines = "\n".join(
        f"  - {s['sector']}: avg daily return {s['avg_return']:+.3f}%, avg 20D vol {s['avg_vol']:.1f}%"
        for s in sectors
    )
    ticker_lines = "\n".join(
        f"  - {d['ticker']} ({d['company_name']}, {d['sector']}): "
        f"close ${d['close_price']}, day {d['daily_return_pct']:+.3f}%, "
        f"20D vol {d['vol_20d_pct']:.1f}%, 52W position {d['position_52w_pct']:.0f}%"
        for d in daily
    )

    return f"""You are a senior equity analyst writing a concise daily market briefing for a data engineering portfolio dashboard. 
Today's date is {data['as_of_date']}.

Write a structured market briefing in markdown format with these exact sections:
1. **Market Overview** (2-3 sentences summarising today's action)
2. **Today's Movers** (highlight top gainer and loser with context)
3. **Sector Snapshot** (1-2 sentences on sector rotation or themes)
4. **Macro Environment** (2-3 sentences interpreting the current rate/inflation context)
5. **52-Week Perspective** (1-2 sentences on which stocks have been strongest/weakest)
6. **Key Risks to Watch** (2-3 bullet points of risks relevant to the data)

Use specific numbers from the data provided. Be concise — no more than 300 words total.
Write in professional analyst style: confident, factual, no disclaimers.

---
MARKET DATA AS OF {data['as_of_date']}:

Stock performance today:
{ticker_lines}

Top gainer: {top_gainer['ticker']} +{top_gainer['daily_return_pct']:.3f}%
Top loser:  {top_loser['ticker']} {top_loser['daily_return_pct']:.3f}%
Gainers: {len(gainers)}/10   Losers: {len(losers)}/10

Sector performance:
{sector_lines}

Macro indicators:
  - Fed Funds Rate: {macro['fed_funds_rate']}%
  - 10Y Treasury Yield: {macro['treasury_yield_10y']}%
  - Real Yield (10Y): {macro['real_yield_10y']}%
  - Breakeven Inflation (10Y): {macro['breakeven_inflation_10y']}%
  - Unemployment Rate: {macro['unemployment_rate']}%
  - GDP Growth Rate (latest): {macro['gdp_growth_rate']}%

52-Week leaders/laggards:
  - Best:  {best_52w['ticker']} ({best_52w['company_name']}) +{best_52w['return_52w_pct']:.1f}%
  - Worst: {worst_52w['ticker']} ({worst_52w['company_name']}) {worst_52w['return_52w_pct']:.1f}%
"""


# ── Gemini API call ───────────────────────────────────────────────────────────

def _call_gemini(prompt: str) -> str:
    """Send prompt to Gemini and return the response text."""
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. Add it to your .env file or GitHub secrets."
        )

    client = genai.Client(api_key=api_key)
    logger.info("Calling Gemini API (model: gemini-2.5-flash)...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


# ── Output writing ────────────────────────────────────────────────────────────

def _write_briefing(briefing_text: str, as_of_date: str) -> None:
    """Write the AI briefing to the Evidence dashboard page."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    content = f"""---
title: AI Market Briefing
---

<Alert status="info">
This briefing is generated by Gemini AI based on real market data as of **{as_of_date}**. 
It refreshes automatically on each pipeline deployment.
Generated at: {generated_at}
</Alert>

{briefing_text}

---

*Powered by [Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/) · 
Data: Yahoo Finance + FRED Federal Reserve · 
Pipeline: dbt + Dagster · 
Dashboard: [Evidence](https://evidence.dev)*
"""

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    logger.info("Briefing written to %s", OUTPUT_PATH)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate AI market briefing")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompt and response without writing the file")
    args = parser.parse_args()

    logger.info("Fetching market data (target: %s)...", TARGET.upper())

    if TARGET == "bigquery":
        data = _fetch_from_bigquery()
    else:
        data = _fetch_from_duckdb()

    logger.info("Data fetched for %s (%d tickers)", data["as_of_date"], len(data["daily"]))

    prompt = _build_prompt(data)

    if args.dry_run:
        print("\n" + "=" * 60 + "\nPROMPT:\n" + "=" * 60)
        print(prompt)

    briefing = _call_gemini(prompt)

    if args.dry_run:
        print("\n" + "=" * 60 + "\nRESPONSE:\n" + "=" * 60)
        print(briefing)
        return

    _write_briefing(briefing, data["as_of_date"])
    logger.info("Done! Briefing page ready at dashboard/pages/briefing.md")


if __name__ == "__main__":
    main()
