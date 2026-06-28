-- Sector-level performance summary
-- Percentage values divided by 100 so Evidence's % format displays correctly.
select
    f.sector,
    count(distinct f.ticker)                                              as num_stocks,
    round(avg(f.daily_return_pct) / 100.0, 6)                           as avg_daily_return_pct,
    round(avg(f.volatility_20d_annualized) / 100.0, 4)                  as avg_volatility_20d_pct,
    round(avg(f.volume), 0)                                               as avg_volume,
    round(avg(f.close_price / nullif(f.sma_200d, 0) - 1), 4)            as avg_pct_above_200sma
from main_marts.fct_daily_trading f
where f.trading_date = (select max(trading_date) from main_marts.fct_daily_trading)
group by f.sector
order by avg_daily_return_pct desc
