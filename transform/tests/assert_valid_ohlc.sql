-- Custom test: Prices must be positive and internally consistent
-- A row fails if any OHLC price is zero/negative, or if the OHLC
-- relationship is violated (high must be >= open, close, low; low must be <=).

select
    price_id,
    ticker,
    trading_date,
    open_price,
    high_price,
    low_price,
    close_price
from {{ ref('stg_stock_prices') }}
where
    open_price  <= 0
    or high_price  <= 0
    or low_price   <= 0
    or close_price <= 0
    or high_price < open_price
    or high_price < close_price
    or high_price < low_price
    or low_price  > open_price
    or low_price  > close_price
