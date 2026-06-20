-- Macro indicators — latest values and 12-month history
select
    trading_date,
    fed_funds_rate,
    cpi,
    unemployment_rate,
    treasury_yield_10y,
    gdp_growth_rate,
    breakeven_inflation_10y,
    real_yield_10y
from main_marts.fct_daily_trading
where ticker = 'AAPL'   -- one ticker to deduplicate dates
order by trading_date
