"""Load raw Parquet files into DuckDB.

This module reads extracted Parquet files from the data/raw/ directory
and loads them into a DuckDB database in the 'raw' schema, preserving
the original data for downstream dbt transformations.
"""

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_DB_PATH = Path("data/processed/finance.duckdb")


def load_to_duckdb(
    raw_dir: Path | None = None,
    db_path: Path | None = None,
) -> list[str]:
    """Load all Parquet files from raw directory into DuckDB.

    Creates a 'raw' schema and loads each Parquet file as a table.
    Stock price files are consolidated into a single 'raw_stock_prices' table.
    Company info is loaded as 'raw_company_info'.

    Args:
        raw_dir: Directory containing raw Parquet files. Defaults to data/raw/.
        db_path: Path to DuckDB database file. Defaults to data/processed/finance.duckdb.

    Returns:
        List of table names that were loaded.
    """
    raw_dir = raw_dir or DEFAULT_RAW_DIR
    db_path = db_path or DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))
    loaded_tables: list[str] = []

    try:
        # Create the raw schema
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")

        # Load all stock price files into a single table
        price_files = list(raw_dir.glob("*_prices.parquet"))
        if price_files:
            logger.info("Loading %d stock price files...", len(price_files))

            # Use DuckDB's glob to read all price parquet files at once
            con.execute(
                """
                CREATE OR REPLACE TABLE raw.raw_stock_prices AS
                SELECT * FROM read_parquet(?)
                """,
                [str(raw_dir / "*_prices.parquet")],
            )

            row_count = con.execute(
                "SELECT COUNT(*) FROM raw.raw_stock_prices"
            ).fetchone()[0]
            logger.info("Loaded %d rows into raw.raw_stock_prices", row_count)
            loaded_tables.append("raw.raw_stock_prices")

        # Load company info
        company_file = raw_dir / "company_info.parquet"
        if company_file.exists():
            logger.info("Loading company info...")
            con.execute(
                """
                CREATE OR REPLACE TABLE raw.raw_company_info AS
                SELECT * FROM read_parquet(?)
                """,
                [str(company_file)],
            )

            row_count = con.execute(
                "SELECT COUNT(*) FROM raw.raw_company_info"
            ).fetchone()[0]
            logger.info("Loaded %d rows into raw.raw_company_info", row_count)
            loaded_tables.append("raw.raw_company_info")

        # Load economic indicators (optional — only present if FRED extraction has run)
        indicators_file = raw_dir / "economic_indicators.parquet"
        if indicators_file.exists():
            logger.info("Loading economic indicators...")
            con.execute(
                """
                CREATE OR REPLACE TABLE raw.raw_economic_indicators AS
                SELECT * FROM read_parquet(?)
                """,
                [str(indicators_file)],
            )

            row_count = con.execute(
                "SELECT COUNT(*) FROM raw.raw_economic_indicators"
            ).fetchone()[0]
            logger.info("Loaded %d rows into raw.raw_economic_indicators", row_count)
            loaded_tables.append("raw.raw_economic_indicators")

        # Log summary
        logger.info("Load complete. Tables loaded: %s", loaded_tables)

    finally:
        con.close()

    return loaded_tables


def verify_load(db_path: Path | None = None) -> None:
    """Print a summary of all tables in the raw schema for verification."""
    db_path = db_path or DEFAULT_DB_PATH
    con = duckdb.connect(str(db_path))

    try:
        tables = con.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema = 'raw'
            ORDER BY table_name
            """
        ).fetchall()

        print("\n" + "=" * 60)
        print("DuckDB Raw Schema Summary")
        print("=" * 60)

        for schema, table in tables:
            row_count = con.execute(
                f"SELECT COUNT(*) FROM {schema}.{table}"
            ).fetchone()[0]
            col_count = con.execute(
                f"SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = '{table}'"
            ).fetchone()[0]
            print(f"  {schema}.{table}: {row_count:,} rows, {col_count} columns")

        print("=" * 60 + "\n")

    finally:
        con.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )
    load_to_duckdb()
    verify_load()
