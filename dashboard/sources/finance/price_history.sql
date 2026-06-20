-- Daily price history for all tickers
select
    ticker,
    trading_date,
    open_price,
    high_52w,
    low_52w,
    close_price,
    volume,
    daily_return_pct,
    log_return_pct,
    sma_30d,
    sma_200d,
    volatility_20d_annualized,
    price_position_52w,
    relative_volume_20d
from main_marts.fct_daily_trading
order by ticker, trading_date
