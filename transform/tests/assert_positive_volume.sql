-- Custom data test: Ensure all raw stock records have positive volume
-- Tests the source table directly, before staging silently drops bad rows.
-- This catches data quality issues coming from Yahoo Finance extraction.

select
    ticker,
    date,
    volume
from {{ source('raw', 'raw_stock_prices') }}
where volume <= 0
