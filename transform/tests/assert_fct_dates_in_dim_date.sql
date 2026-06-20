-- Custom test: Every trading date in the fact table must exist in dim_date
-- Ensures the date dimension is wide enough to cover all price data.

select distinct
    f.trading_date
from {{ ref('fct_daily_trading') }} f
left join {{ ref('dim_date') }} d
    on f.trading_date = d.calendar_date
where d.calendar_date is null
