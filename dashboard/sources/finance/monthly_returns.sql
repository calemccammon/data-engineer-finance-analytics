-- Monthly return heatmap data
-- Uses MAX(CASE WHEN rn=1 THEN ... END) instead of first()/last() to stay
-- compatible with both DuckDB (local) and BigQuery (cloud dashboard).
-- Returns are expressed as decimals (e.g. 0.05 = 5%) for Evidence % formatting.
with ranked as (
    select
        ticker,
        close_price,
        trading_date - (cast(extract(day from trading_date) as integer) - 1) as month_start,
        row_number() over (partition by ticker, trading_date - (cast(extract(day from trading_date) as integer) - 1) order by trading_date asc)  as rn_asc,
        row_number() over (partition by ticker, trading_date - (cast(extract(day from trading_date) as integer) - 1) order by trading_date desc) as rn_desc,
        count(*) over (partition by ticker, trading_date - (cast(extract(day from trading_date) as integer) - 1)) as trading_days
    from main_marts.fct_daily_trading
)

select
    ticker,
    month_start                                                     as month,
    round(
        (max(case when rn_desc = 1 then close_price end) /
         max(case when rn_asc  = 1 then close_price end) - 1),
        4
    ) as monthly_return_pct,
    max(trading_days) as trading_days
from ranked
group by ticker, month_start
order by ticker, month_start
