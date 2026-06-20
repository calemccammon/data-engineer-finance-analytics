-- Latest snapshot per ticker with performance metrics
select
    f.ticker,
    f.company_name,
    f.sector,
    c.industry,
    c.market_cap_category,
    c.exchange,
    f.close_price                                              as latest_close,
    f.daily_return_pct,
    f.volume,
    f.sma_30d,
    f.sma_200d,
    round(f.volatility_20d_annualized, 2)               as volatility_20d_pct,
    f.trading_date                                             as as_of_date
from main_marts.fct_daily_trading f
join main_marts.dim_company c using (ticker)
where f.trading_date = (select max(trading_date) from main_marts.fct_daily_trading)
order by f.company_name
