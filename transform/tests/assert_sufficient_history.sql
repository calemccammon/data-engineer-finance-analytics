-- Custom test: Every ticker should have at least 200 trading days of history
-- This is the minimum needed for the SMA-200d to be meaningful.
-- Adjust the threshold if you use a shorter history window.

select
    ticker,
    count(*) as trading_day_count
from {{ ref('stg_stock_prices') }}
group by ticker
having count(*) < 200
