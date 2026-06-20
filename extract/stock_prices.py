"""Extract historical stock price data from Yahoo Finance.

This module pulls OHLCV (Open, High, Low, Close, Volume) data for a 
configurable list of stock tickers using the yfinance library.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Default tickers: diverse S&P 500 mix across sectors
DEFAULT_TICKERS = [
    "AAPL",   # Tech - Apple
    "MSFT",   # Tech - Microsoft
    "GOOGL",  # Tech - Alphabet
    "AMZN",   # Consumer - Amazon
    "NVDA",   # Tech - NVIDIA
    "TSLA",   # Auto - Tesla
    "JPM",    # Finance - JPMorgan
    "JNJ",    # Healthcare - Johnson & Johnson
    "V",      # Payments - Visa
    "META",   # Tech - Meta
]

DEFAULT_RAW_DIR = Path("data/raw")


def extract_stock_prices(
    tickers: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Extract historical stock prices and save as Parquet files.

    Args:
        tickers: List of stock ticker symbols. Defaults to DEFAULT_TICKERS.
        start_date: Start date in YYYY-MM-DD format. Defaults to 2 years ago.
        end_date: End date in YYYY-MM-DD format. Defaults to today.
        output_dir: Directory to save Parquet files. Defaults to data/raw/.

    Returns:
        Dictionary mapping ticker symbols to their output file paths.
    """
    tickers = tickers or DEFAULT_TICKERS
    output_dir = output_dir or DEFAULT_RAW_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if start_date is None:
        start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(
        "Extracting prices for %d tickers from %s to %s",
        len(tickers),
        start_date,
        end_date,
    )

    output_files: dict[str, Path] = {}

    for ticker in tickers:
        try:
            logger.info("Downloading %s...", ticker)
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date)

            if df.empty:
                logger.warning("No data returned for %s, skipping.", ticker)
                continue

            # Clean up the dataframe
            df = df.reset_index()
            df["ticker"] = ticker
            df["extracted_at"] = datetime.now().isoformat()

            # Normalize column names to snake_case
            df.columns = [
                col.lower().replace(" ", "_") for col in df.columns
            ]

            # Save as Parquet (columnar, compressed, efficient)
            output_path = output_dir / f"{ticker.lower()}_prices.parquet"
            df.to_parquet(output_path, index=False)
            output_files[ticker] = output_path

            logger.info(
                "Saved %d rows for %s to %s",
                len(df),
                ticker,
                output_path,
            )

        except Exception:
            logger.exception("Failed to extract data for %s", ticker)

    logger.info(
        "Extraction complete. Successfully extracted %d/%d tickers.",
        len(output_files),
        len(tickers),
    )
    return output_files


def extract_company_info(
    tickers: list[str] | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Extract company metadata (sector, industry, market cap, etc.).

    Args:
        tickers: List of stock ticker symbols. Defaults to DEFAULT_TICKERS.
        output_dir: Directory to save the output file. Defaults to data/raw/.

    Returns:
        Path to the saved company info Parquet file.
    """
    tickers = tickers or DEFAULT_TICKERS
    output_dir = output_dir or DEFAULT_RAW_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    companies = []
    for ticker in tickers:
        try:
            logger.info("Fetching company info for %s...", ticker)
            stock = yf.Ticker(ticker)
            info = stock.info

            companies.append({
                "ticker": ticker,
                "company_name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap"),
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", ""),
                "country": info.get("country", ""),
                "website": info.get("website", ""),
                "extracted_at": datetime.now().isoformat(),
            })
        except Exception:
            logger.exception("Failed to fetch info for %s", ticker)

    df = pd.DataFrame(companies)
    output_path = output_dir / "company_info.parquet"
    df.to_parquet(output_path, index=False)

    logger.info("Saved company info for %d companies to %s", len(df), output_path)
    return output_path


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )
    extract_stock_prices()
    extract_company_info()
