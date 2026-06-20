"""Software-defined assets for the Finance Analytics Pipeline.

Asset graph (dependency order):
    raw_stock_prices ──┐
                       ├──▶ raw_tables ──▶ dbt_staging ──▶ dbt_intermediate ──▶ dbt_marts
    raw_company_info ──┘

The active warehouse target (local DuckDB or BigQuery) is controlled by the
TARGET environment variable. All assets are warehouse-agnostic.
"""

import logging
import io
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from dagster import (
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    asset,
)

from extract.stock_prices import extract_company_info, extract_stock_prices
from extract.economic_indicators import extract_economic_indicators
from load.loader import DEFAULT_DB_PATH, load_to_duckdb

logger = logging.getLogger(__name__)

DBT_PROJECT_DIR = Path(__file__).parent.parent / "transform"
FINANCE_DB_PATH = Path(__file__).parent.parent / "data" / "processed" / "finance.duckdb"
TARGET = os.environ.get("TARGET", "local")


def _run_dbt(context: AssetExecutionContext, *args: str) -> str:
    """Run a dbt command via the Python API and stream output to Dagster logs. Returns captured output."""
    from dbt.cli.main import dbtRunner

    os.environ.setdefault("FINANCE_DB_PATH", str(FINANCE_DB_PATH))
    os.environ.setdefault("DBT_TARGET", TARGET)

    invoke_args = [
        *args,
        "--project-dir", str(DBT_PROJECT_DIR),
        "--profiles-dir", str(DBT_PROJECT_DIR),
        "--target", TARGET,
    ]
    context.log.info("Running dbt %s (target=%s)", " ".join(args), TARGET)

    buf = io.StringIO()
    def _capture(event):
        try:
            msg = event.info.msg
        except AttributeError:
            msg = str(event)
        if msg:
            buf.write(msg + "\n")
    runner = dbtRunner(callbacks=[_capture])
    result = runner.invoke(invoke_args)

    output = buf.getvalue()
    if output:
        context.log.info(output)
    if result.exception:
        raise result.exception
    return output


# ---------------------------------------------------------------------------
# Extract assets
# ---------------------------------------------------------------------------


@asset(
    group_name="extract",
    description="Historical OHLCV price data for all configured tickers, saved as Parquet files.",
)
def raw_stock_prices(context: AssetExecutionContext) -> MaterializeResult:
    """Pull historical stock prices from Yahoo Finance → data/raw/."""
    output_files = extract_stock_prices()

    import pandas as pd
    total_rows = sum(pd.read_parquet(p).shape[0] for p in output_files.values())

    return MaterializeResult(
        metadata={
            "tickers": MetadataValue.json(list(output_files.keys())),
            "files_written": MetadataValue.int(len(output_files)),
            "total_rows": MetadataValue.int(total_rows),
        }
    )


@asset(
    group_name="extract",
    description="Company metadata (sector, industry, market cap) for all tickers.",
)
def raw_company_info(context: AssetExecutionContext) -> MaterializeResult:
    """Pull company metadata from Yahoo Finance → data/raw/company_info.parquet."""
    output_path = extract_company_info()

    import pandas as pd
    df = pd.read_parquet(output_path)

    return MaterializeResult(
        metadata={
            "rows": MetadataValue.int(len(df)),
            "output_path": MetadataValue.path(str(output_path)),
        }
    )


@asset(
    group_name="extract",
    description="Macroeconomic indicators from FRED (Fed Funds Rate, CPI, unemployment, treasury yields, GDP).",
)
def raw_economic_indicators(context: AssetExecutionContext) -> MaterializeResult:
    """Pull macroeconomic series from FRED API → data/raw/economic_indicators.parquet."""
    output_path = extract_economic_indicators()

    import pandas as pd
    df = pd.read_parquet(output_path)
    series_counts = df.groupby("series_id").size().to_dict()

    return MaterializeResult(
        metadata={
            "total_rows": MetadataValue.int(len(df)),
            "series": MetadataValue.json(series_counts),
            "output_path": MetadataValue.path(str(output_path)),
        }
    )


# ---------------------------------------------------------------------------
# Load asset
# ---------------------------------------------------------------------------


@asset(
    group_name="load",
    deps=[raw_stock_prices, raw_company_info, raw_economic_indicators],
    description="Load all raw Parquet files into the active target (DuckDB or BigQuery).",
)
def raw_tables(context: AssetExecutionContext) -> MaterializeResult:
    """Load extracted Parquet files into the warehouse configured by TARGET."""
    context.log.info("Load target: %s", TARGET.upper())

    if TARGET == "bigquery":
        from load.bigquery_loader import load_to_bigquery
        loaded_tables = load_to_bigquery()
        return MaterializeResult(
            metadata={"tables_loaded": MetadataValue.json(loaded_tables), "target": MetadataValue.text("bigquery")}
        )
    else:
        loaded_tables = load_to_duckdb()
        import duckdb
        con = duckdb.connect(str(DEFAULT_DB_PATH))
        row_counts = {
            t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in loaded_tables
        }
        con.close()
        return MaterializeResult(
            metadata={
                "tables_loaded": MetadataValue.json(loaded_tables),
                "row_counts": MetadataValue.json(row_counts),
                "target": MetadataValue.text("local"),
            }
        )


# ---------------------------------------------------------------------------
# dbt assets — one asset per dbt layer, each depending on the previous.
# Each asset invokes dbt via the Python API (dbtRunner), demonstrating the
# full orchestration DAG in the Dagster UI.
# ---------------------------------------------------------------------------


@asset(
    group_name="dbt",
    deps=[raw_tables],
    description="dbt seeds: load static reference CSV files into the warehouse (e.g. sp500_companies).",
)
def dbt_seeds(context: AssetExecutionContext) -> MaterializeResult:
    """Run dbt seed — loads CSV files from transform/seeds/ into DuckDB."""
    stdout = _run_dbt(context, "seed")
    lines = [l for l in stdout.splitlines() if "OK" in l or "ERROR" in l or "seed" in l.lower()]
    return MaterializeResult(
        metadata={"dbt_output": MetadataValue.md("```\n" + "\n".join(lines[-20:]) + "\n```")}
    )


@asset(
    group_name="dbt",
    deps=[dbt_seeds],
    description="dbt staging models: clean 1:1 copies of raw source tables.",
)
def dbt_staging(context: AssetExecutionContext) -> MaterializeResult:
    """Run dbt staging layer (stg_stock_prices, stg_company_info)."""
    stdout = _run_dbt(context, "run", "--select", "staging")
    lines = [l for l in stdout.splitlines() if "OK" in l or "ERROR" in l or "model" in l.lower()]
    return MaterializeResult(
        metadata={"dbt_output": MetadataValue.md("```\n" + "\n".join(lines[-20:]) + "\n```")}
    )


@asset(
    group_name="dbt",
    deps=[dbt_staging],
    description="dbt intermediate models: returns, moving averages, volatility.",
)
def dbt_intermediate(context: AssetExecutionContext) -> MaterializeResult:
    """Run dbt intermediate layer (int_daily_returns, int_moving_averages, int_volatility)."""
    stdout = _run_dbt(context, "run", "--select", "intermediate")
    lines = [l for l in stdout.splitlines() if "OK" in l or "ERROR" in l or "model" in l.lower()]
    return MaterializeResult(
        metadata={"dbt_output": MetadataValue.md("```\n" + "\n".join(lines[-20:]) + "\n```")}
    )


@asset(
    group_name="dbt",
    deps=[dbt_intermediate],
    description="dbt mart models: fct_daily_trading, dim_company, dim_date.",
)
def dbt_marts(context: AssetExecutionContext) -> MaterializeResult:
    """Run dbt marts layer (fct_daily_trading, dim_company, dim_date)."""
    stdout = _run_dbt(context, "run", "--select", "marts")
    lines = [l for l in stdout.splitlines() if "OK" in l or "ERROR" in l or "model" in l.lower()]
    return MaterializeResult(
        metadata={"dbt_output": MetadataValue.md("```\n" + "\n".join(lines[-20:]) + "\n```")}
    )


@asset(
    group_name="dbt",
    deps=[dbt_marts],
    description="Run all dbt schema and custom data quality tests.",
)
def dbt_tests(context: AssetExecutionContext) -> MaterializeResult:
    """Run `dbt test` — all schema tests and custom SQL tests."""
    stdout = _run_dbt(context, "test")
    passed = stdout.count("PASS")
    failed = stdout.count("FAIL")
    return MaterializeResult(
        metadata={
            "tests_passed": MetadataValue.int(passed),
            "tests_failed": MetadataValue.int(failed),
            "dbt_output": MetadataValue.md("```\n" + stdout[-2000:] + "\n```"),
        }
    )

