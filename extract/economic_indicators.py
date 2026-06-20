"""Extract macroeconomic indicator data from the FRED API.

Uses the `fredapi` Python library. Requires a free API key from:
    https://fred.stlouisfed.org/docs/api/api_key.html

Set FRED_API_KEY in your .env file or environment before running.
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from fredapi import Fred

# find_dotenv() walks up parent directories until it finds .env — works
# regardless of which directory the process was launched from.
load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("data/raw")

# FRED series to pull — chosen for their relevance to equity analysis
FRED_SERIES = {
    "FEDFUNDS":        "Federal Funds Effective Rate (%)",
    "CPIAUCSL":        "Consumer Price Index (All Urban, All Items)",
    "UNRATE":          "Civilian Unemployment Rate (%)",
    "DGS10":           "10-Year Treasury Constant Maturity Rate (%)",
    "A191RL1Q225SBEA": "Real GDP Growth Rate (quarterly, %)",
    "T10YIE":          "10-Year Breakeven Inflation Rate (%)",
}


def _get_fred_client() -> Fred:
    """Return an authenticated FRED client, raising clearly if key is missing."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise EnvironmentError(
            "FRED_API_KEY is not set. Add it to your .env file:\n"
            "  FRED_API_KEY=your_actual_key\n"
            "Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    return Fred(api_key=api_key)


def extract_economic_indicators(
    series: dict[str, str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Extract macroeconomic indicators from FRED and save as a single Parquet file.

    Each indicator series is fetched individually and concatenated into one
    long-format DataFrame: one row per (series_id, date) observation.

    Args:
        series: Dict mapping FRED series IDs to human-readable names.
                Defaults to FRED_SERIES.
        start_date: Start date (YYYY-MM-DD). Defaults to 5 years ago.
        end_date: End date (YYYY-MM-DD). Defaults to today.
        output_dir: Output directory. Defaults to data/raw/.

    Returns:
        Path to the saved Parquet file.
    """
    series = series or FRED_SERIES
    output_dir = output_dir or DEFAULT_RAW_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    fred = _get_fred_client()
    records = []

    for series_id, description in series.items():
        try:
            logger.info("Fetching FRED series %s (%s)...", series_id, description)
            data = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)

            if data.empty:
                logger.warning("No data returned for %s, skipping.", series_id)
                continue

            df = data.reset_index()
            df.columns = ["observation_date", "value"]
            df["series_id"] = series_id
            df["series_name"] = description
            df["frequency"] = _infer_frequency(data)
            df["extracted_at"] = datetime.now().isoformat()

            records.append(df)
            logger.info(
                "Fetched %d observations for %s (%s to %s)",
                len(df),
                series_id,
                df["observation_date"].min().strftime("%Y-%m-%d"),
                df["observation_date"].max().strftime("%Y-%m-%d"),
            )

        except Exception:
            logger.exception("Failed to fetch FRED series %s", series_id)

    if not records:
        raise RuntimeError("No FRED data was successfully extracted.")

    combined = pd.concat(records, ignore_index=True)

    output_path = output_dir / "economic_indicators.parquet"
    combined.to_parquet(output_path, index=False)

    logger.info(
        "Saved %d total observations across %d series to %s",
        len(combined),
        len(records),
        output_path,
    )
    return output_path


def _infer_frequency(series: "pd.Series") -> str:
    """Infer the reporting frequency from the gaps between observations."""
    if len(series) < 2:
        return "unknown"
    median_gap = series.index.to_series().diff().median()
    days = median_gap.days if hasattr(median_gap, "days") else 0

    if days <= 1:
        return "daily"
    elif days <= 8:
        return "weekly"
    elif days <= 35:
        return "monthly"
    elif days <= 100:
        return "quarterly"
    return "annual"


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )
    extract_economic_indicators()
