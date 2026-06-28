-- Daily price history for all tickers
-- Percentage values divided by 100 so Evidence's % format displays correctly.
select
    ticker,
    trading_date,
    open_price,
    high_52w,
    low_52w,
    close_price,
    volume,
    daily_return_pct          / 100.0 as daily_return_pct,
    log_return_pct            / 100.0 as log_return_pct,
    sma_30d,
    sma_200d,
    volatility_20d_annualized / 100.0 as volatility_20d_annualized,
    price_position_52w,
    relative_volume_20d
from main_marts.fct_daily_trading
order by ticker, trading_date
