-- 52-week performance leaders and laggards
-- Uses MAX(CASE WHEN rn=1 THEN ... END) instead of first()/last() to stay
-- compatible with both DuckDB (local) and BigQuery (cloud dashboard).
with ranked as (
    select
        ticker,
        company_name,
        sector,
        close_price,
        volatility_20d_annualized,
        volume,
        row_number() over (partition by ticker order by trading_date asc)  as rn_asc,
        row_number() over (partition by ticker order by trading_date desc) as rn_desc
    from main_marts.fct_daily_trading
    where trading_date >= (select max(trading_date) - interval '365 days' from main_marts.fct_daily_trading)
)

select
    ticker,
    company_name,
    sector,
    max(case when rn_asc  = 1 then close_price end) as price_52w_ago,
    max(case when rn_desc = 1 then close_price end) as price_now,
    round(
        (max(case when rn_desc = 1 then close_price end) /
         max(case when rn_asc  = 1 then close_price end) - 1) * 100,
        2
    ) as return_52w_pct,
    round(avg(volatility_20d_annualized), 2) as avg_volatility_pct,
    round(avg(volume), 0)                           as avg_daily_volume
from ranked
group by ticker, company_name, sector
order by return_52w_pct desc
