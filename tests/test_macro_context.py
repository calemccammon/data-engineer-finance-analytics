"""
Tests for the int_macro_context dbt model, run against a small DuckDB database.

The model decides which FRED figure each trading date sees. These tests build
it with dbt from a handful of hand-written observations and check the dates.
"""

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from dbt.cli.main import dbtRunner

from load.loader import load_to_duckdb

TRANSFORM_DIR = Path(__file__).parent.parent / "transform"

# Thursday, Friday, Monday, Monday, Monday
TRADING_DATES = ["2024-02-01", "2024-02-02", "2024-02-05", "2024-02-12", "2024-03-04"]

# (series, observation date, value). The release lags are in dbt_project.yml:
# FEDFUNDS 35 days, UNRATE 42, CPIAUCSL 46, the GDP series 123, the daily ones 0.
OBSERVATIONS = [
    # December's rate is out on 5 January, before the first trading date.
    ("FEDFUNDS", "2023-12-01", 5.33),
    # January's is dated New Year's Day, which never trades. It is out on Monday 5 February.
    ("FEDFUNDS", "2024-01-01", 5.40),
    # Out on Sunday 17 December.
    ("CPIAUCSL", "2023-11-01", 307.0),
    # Out on Friday 16 February, which is not one of the trading dates here.
    ("CPIAUCSL", "2024-01-01", 308.4),
    # The only unemployment figure. Out on Monday 12 February.
    ("UNRATE", "2024-01-01", 3.7),
    # The fourth quarter, dated a Sunday. Out on Thursday 1 February.
    ("A191RL1Q225SBEA", "2023-10-01", 3.2),
    # The first quarter. Not out until 3 May, after the last trading date.
    ("A191RL1Q225SBEA", "2024-01-01", 1.6),
    ("DGS10", "2024-02-01", 3.87),
    ("DGS10", "2024-02-02", 4.03),
    ("DGS10", "2024-02-05", 4.17),
    ("T10YIE", "2024-02-01", 2.25),
    ("T10YIE", "2024-02-02", 2.24),
]


@pytest.fixture(scope="module")
def macro_context(tmp_path_factory):
    """Build int_macro_context from the rows above and return it keyed by trading date."""
    tmp_path = tmp_path_factory.mktemp("macro_context")
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    db_path = tmp_path / "finance.duckdb"

    pd.DataFrame(
        {
            "date": pd.to_datetime(TRADING_DATES),
            "ticker": "AAPL",
            "open": 185.0,
            "high": 187.0,
            "low": 183.5,
            "close": 184.5,
            "volume": 50_000_000,
            "extracted_at": "2024-03-05",
        }
    ).to_parquet(raw_dir / "aapl_prices.parquet", index=False)

    pd.DataFrame(
        {
            "series_id": [series for series, _, _ in OBSERVATIONS],
            "series_name": [series for series, _, _ in OBSERVATIONS],
            "observation_date": pd.to_datetime([day for _, day, _ in OBSERVATIONS]),
            "value": [value for _, _, value in OBSERVATIONS],
            "frequency": "test",
            "extracted_at": "2024-03-05",
        }
    ).to_parquet(raw_dir / "economic_indicators.parquet", index=False)

    load_to_duckdb(raw_dir=raw_dir, db_path=db_path)

    with pytest.MonkeyPatch.context() as env:
        env.setenv("FINANCE_DB_PATH", str(db_path))
        env.setenv("DBT_TARGET", "local")
        paths = ["--project-dir", str(TRANSFORM_DIR), "--profiles-dir", str(TRANSFORM_DIR)]
        runner = dbtRunner()
        # The staging models use dbt_utils
        assert runner.invoke(["deps", *paths]).success
        result = runner.invoke(
            [
                "run",
                "--select",
                "+int_macro_context",
                "--target-path",
                str(tmp_path / "target"),
                "--log-path",
                str(tmp_path / "logs"),
                *paths,
            ]
        )
        assert result.success, result.exception

    # dbt ran in this process and still holds the file open for writing, so a
    # read-only connection to it would be refused.
    con = duckdb.connect(str(db_path))
    try:
        rows = con.execute(
            "SELECT * FROM main_intermediate.int_macro_context ORDER BY calendar_date"
        ).fetch_df()
    finally:
        con.close()
    rows["calendar_date"] = pd.to_datetime(rows["calendar_date"]).dt.date
    return rows.set_index("calendar_date")


def _on(macro_context, day: str, column: str):
    value = macro_context.loc[date.fromisoformat(day), column]
    return None if pd.isna(value) else value


def test_one_row_per_trading_date(macro_context):
    assert [day.isoformat() for day in macro_context.index] == TRADING_DATES


def test_a_figure_released_before_the_first_trading_date_is_already_in_force(macro_context):
    assert _on(macro_context, "2024-02-01", "fed_funds_rate") == 5.33


def test_a_figure_is_not_used_before_it_is_released(macro_context):
    # January's rate describes January but is not out until 5 February
    assert _on(macro_context, "2024-02-01", "fed_funds_rate") == 5.33
    assert _on(macro_context, "2024-02-02", "fed_funds_rate") == 5.33
    # The first quarter's growth is never out within these dates
    assert _on(macro_context, "2024-03-04", "gdp_growth_rate") == 3.2


def test_a_figure_is_in_force_on_the_day_it_is_released(macro_context):
    assert _on(macro_context, "2024-02-05", "fed_funds_rate") == 5.40
    assert _on(macro_context, "2024-02-01", "gdp_growth_rate") == 3.2
    assert _on(macro_context, "2024-02-12", "unemployment_rate") == 3.7


def test_an_observation_dated_on_a_day_with_no_trading_is_kept(macro_context):
    # Dated 1 January (a holiday) and 1 October (a Sunday)
    assert _on(macro_context, "2024-03-04", "fed_funds_rate") == 5.40
    assert _on(macro_context, "2024-02-02", "gdp_growth_rate") == 3.2


def test_a_figure_released_between_trading_dates_shows_on_the_next_one(macro_context):
    # Released on Sunday 17 December
    assert _on(macro_context, "2024-02-01", "cpi") == 307.0
    # Released on 16 February, between two of the trading dates
    assert _on(macro_context, "2024-02-12", "cpi") == 307.0
    assert _on(macro_context, "2024-03-04", "cpi") == 308.4


def test_a_series_has_no_value_before_its_first_release(macro_context):
    assert _on(macro_context, "2024-02-05", "unemployment_rate") is None


def test_a_daily_rate_is_carried_over_a_day_with_no_observation(macro_context):
    assert _on(macro_context, "2024-02-02", "treasury_yield_10y") == 4.03
    assert _on(macro_context, "2024-02-05", "treasury_yield_10y") == 4.17
    assert _on(macro_context, "2024-02-05", "breakeven_inflation_10y") == 2.24
    assert _on(macro_context, "2024-02-12", "treasury_yield_10y") == 4.17


def test_real_yield_is_the_treasury_yield_less_breakeven_inflation(macro_context):
    assert _on(macro_context, "2024-02-01", "real_yield_10y") == pytest.approx(1.62)
    assert _on(macro_context, "2024-02-05", "real_yield_10y") == pytest.approx(1.93)
