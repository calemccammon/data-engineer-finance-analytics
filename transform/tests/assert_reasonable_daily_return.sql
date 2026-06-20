-- Custom test: Daily return must be within a plausible range
-- A single-day return outside ±75% is almost certainly a data error
-- (real circuit breakers halt trading well before that threshold).
-- Returns any rows that look anomalous.

select
    price_id,
    ticker,
    trading_date,
    daily_return_pct
from {{ ref('int_daily_returns') }}
where
    daily_return_pct is not null
    and abs(daily_return_pct) > 75
