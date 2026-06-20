"""Unit tests for the extraction module."""

from extract.stock_prices import DEFAULT_TICKERS


def test_default_tickers_not_empty():
    """Verify we have default tickers configured."""
    assert len(DEFAULT_TICKERS) > 0


def test_default_tickers_are_strings():
    """Verify all tickers are non-empty strings."""
    for ticker in DEFAULT_TICKERS:
        assert isinstance(ticker, str)
        assert len(ticker) > 0
