-- Macro indicators — latest values and 12-month history
-- Rates/yields are stored as whole percentages (e.g. 5.33 for 5.33%).
-- Divide by 100 so Evidence's % format displays them correctly.
select
    trading_date,
    fed_funds_rate          / 100.0 as fed_funds_rate,
    cpi,                                                -- index value, not a percentage
    unemployment_rate       / 100.0 as unemployment_rate,
    treasury_yield_10y      / 100.0 as treasury_yield_10y,
    gdp_growth_rate         / 100.0 as gdp_growth_rate,
    breakeven_inflation_10y / 100.0 as breakeven_inflation_10y,
    real_yield_10y          / 100.0 as real_yield_10y
from main_marts.fct_daily_trading
where ticker = 'AAPL'   -- one ticker to deduplicate dates
order by trading_date
