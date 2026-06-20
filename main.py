"""Finance Analytics Pipeline — CLI entry point.

Run the full ELT pipeline: Extract → Load → Transform.

Usage:
    uv run python main.py              # Run full pipeline
    uv run python main.py extract      # Extract only
    uv run python main.py load         # Load only  
    uv run python main.py transform    # Transform (dbt) only

Target:
    Controlled by TARGET in .env (default: local).
    Set TARGET=bigquery (plus BQ_PROJECT, BQ_KEYFILE) to run against BigQuery.
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

TARGET = os.environ.get("TARGET", "local")

# DuckDB path — only needed when TARGET=local
os.environ.setdefault(
    "FINANCE_DB_PATH",
    str(Path(__file__).parent / "data" / "processed" / "finance.duckdb"),
)

# Keep dbt in sync with TARGET
os.environ.setdefault("DBT_TARGET", TARGET)

from extract.stock_prices import extract_company_info, extract_stock_prices
from extract.economic_indicators import extract_economic_indicators

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
)
logger = logging.getLogger(__name__)


def run_extract():
    """Run the extraction step."""
    logger.info("=" * 60)
    logger.info("STEP 1: EXTRACT — Pulling data from Yahoo Finance & FRED")
    logger.info("=" * 60)
    extract_stock_prices()
    extract_company_info()
    extract_economic_indicators()


def run_load():
    """Run the loading step — routes to DuckDB or BigQuery based on TARGET."""
    logger.info("=" * 60)
    logger.info("STEP 2: LOAD — Target: %s", TARGET.upper())
    logger.info("=" * 60)

    if TARGET == "bigquery":
        from load.bigquery_loader import load_to_bigquery
        load_to_bigquery()
    else:
        from load.loader import load_to_duckdb, verify_load
        load_to_duckdb()
        verify_load()


def run_transform():
    """Run dbt transformations against the active target."""
    from dbt.cli.main import dbtRunner

    logger.info("=" * 60)
    logger.info("STEP 3: TRANSFORM — Running dbt (target: %s)", TARGET)
    logger.info("=" * 60)
    runner = dbtRunner()
    result = runner.invoke(
        ["run", "--project-dir", "transform", "--profiles-dir", "transform"]
    )
    if result.exception:
        raise result.exception


def main():
    """Run the full ELT pipeline or a specific step."""
    logger.info("Pipeline target: %s", TARGET.upper())

    steps = {
        "extract": run_extract,
        "load": run_load,
        "transform": run_transform,
    }

    if len(sys.argv) > 1:
        step_name = sys.argv[1].lower()
        if step_name not in steps:
            print(f"Unknown step: {step_name}")
            print(f"Available steps: {', '.join(steps.keys())}")
            sys.exit(1)
        steps[step_name]()
    else:
        logger.info("Running full ELT pipeline...")
        for step_fn in steps.values():
            step_fn()
        logger.info("Pipeline complete!")


if __name__ == "__main__":
    main()


