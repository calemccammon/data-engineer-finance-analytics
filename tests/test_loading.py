"""Unit tests for the loading module."""

import tempfile
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from load.loader import load_to_duckdb, verify_load


@pytest.fixture
def raw_dir(tmp_path):
    """Create a temporary raw directory with sample Parquet files."""
    raw = tmp_path / "raw"
    raw.mkdir()

    # Create a minimal stock prices Parquet file
    prices_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "open": [185.0, 184.0, 186.0],
            "high": [187.0, 185.5, 188.0],
            "low": [183.5, 182.0, 185.0],
            "close": [184.5, 185.0, 187.5],
            "volume": [50_000_000, 48_000_000, 55_000_000],
            "extracted_at": ["2024-01-05"] * 3,
        }
    )
    prices_df.to_parquet(raw / "aapl_prices.parquet", index=False)

    # Create a minimal company info Parquet file
    company_df = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "company_name": ["Apple Inc."],
            "sector": ["Technology"],
            "industry": ["Consumer Electronics"],
            "market_cap": [3_000_000_000_000],
            "currency": ["USD"],
            "exchange": ["NMS"],
            "country": ["United States"],
            "website": ["https://www.apple.com"],
            "extracted_at": ["2024-01-05"],
        }
    )
    company_df.to_parquet(raw / "company_info.parquet", index=False)

    return raw


@pytest.fixture
def db_path(tmp_path):
    """Return a temporary DuckDB path."""
    return tmp_path / "processed" / "test_finance.duckdb"


def test_load_creates_raw_schema(raw_dir, db_path):
    """Loader should create a 'raw' schema in DuckDB."""
    load_to_duckdb(raw_dir=raw_dir, db_path=db_path)

    con = duckdb.connect(str(db_path))
    schemas = [r[0] for r in con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()]
    con.close()

    assert "raw" in schemas


def test_load_creates_stock_prices_table(raw_dir, db_path):
    """Loader should create raw.raw_stock_prices table."""
    tables = load_to_duckdb(raw_dir=raw_dir, db_path=db_path)

    assert "raw.raw_stock_prices" in tables


def test_load_creates_company_info_table(raw_dir, db_path):
    """Loader should create raw.raw_company_info table."""
    tables = load_to_duckdb(raw_dir=raw_dir, db_path=db_path)

    assert "raw.raw_company_info" in tables


def test_stock_prices_row_count(raw_dir, db_path):
    """Stock prices table should contain the expected number of rows."""
    load_to_duckdb(raw_dir=raw_dir, db_path=db_path)

    con = duckdb.connect(str(db_path))
    count = con.execute("SELECT COUNT(*) FROM raw.raw_stock_prices").fetchone()[0]
    con.close()

    assert count == 3


def test_company_info_row_count(raw_dir, db_path):
    """Company info table should contain the expected number of rows."""
    load_to_duckdb(raw_dir=raw_dir, db_path=db_path)

    con = duckdb.connect(str(db_path))
    count = con.execute("SELECT COUNT(*) FROM raw.raw_company_info").fetchone()[0]
    con.close()

    assert count == 1


def test_load_is_idempotent(raw_dir, db_path):
    """Running load twice should not duplicate rows (CREATE OR REPLACE)."""
    load_to_duckdb(raw_dir=raw_dir, db_path=db_path)
    load_to_duckdb(raw_dir=raw_dir, db_path=db_path)

    con = duckdb.connect(str(db_path))
    count = con.execute("SELECT COUNT(*) FROM raw.raw_stock_prices").fetchone()[0]
    con.close()

    assert count == 3


def test_load_returns_empty_list_when_no_files(tmp_path, db_path):
    """Loader should return an empty list when the raw directory has no Parquet files."""
    empty_raw = tmp_path / "empty_raw"
    empty_raw.mkdir()

    tables = load_to_duckdb(raw_dir=empty_raw, db_path=db_path)

    assert tables == []


def test_verify_load_runs_without_error(raw_dir, db_path, capsys):
    """verify_load should print a summary without raising."""
    load_to_duckdb(raw_dir=raw_dir, db_path=db_path)
    verify_load(db_path=db_path)

    captured = capsys.readouterr()
    assert "raw.raw_stock_prices" in captured.out
