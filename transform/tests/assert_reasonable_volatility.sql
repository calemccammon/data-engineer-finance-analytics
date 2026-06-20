-- Custom test: Volatility values must be within a plausible range
-- Annualized volatility below 1% or above 500% indicates a calculation error.
-- (Most equities sit in the 15–80% annualized vol range.)
-- Only checks rows where we have enough history for the window (non-null values).

select
    price_id,
    ticker,
    trading_date,
    volatility_20d_annualized
from {{ ref('int_volatility') }}
where
    volatility_20d_annualized is not null
    and (
        volatility_20d_annualized < 1
        or volatility_20d_annualized > 500
    )
