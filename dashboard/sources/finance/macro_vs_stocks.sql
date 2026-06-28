-- Rolling 30-day correlation between market return and macro indicators
-- Percentage values divided by 100 so Evidence's % format displays correctly.
-- Rate regime CASE WHEN uses the original column value (before the alias rename).
select
    trading_date,
    ticker,
    daily_return_pct          / 100.0 as daily_return_pct,
    fed_funds_rate            / 100.0 as fed_funds_rate,
    treasury_yield_10y        / 100.0 as treasury_yield_10y,
    unemployment_rate         / 100.0 as unemployment_rate,
    breakeven_inflation_10y   / 100.0 as breakeven_inflation_10y,
    real_yield_10y            / 100.0 as real_yield_10y,
    volatility_20d_annualized / 100.0 as volatility_20d_annualized,
    -- Simple macro regime: rate environment (thresholds reference the raw column)
    case
        when fed_funds_rate >= 5.0 then 'High Rates (≥5%)'
        when fed_funds_rate >= 3.0 then 'Elevated Rates (3–5%)'
        when fed_funds_rate >= 1.0 then 'Normal Rates (1–3%)'
        else 'Low Rates (<1%)'
    end as rate_regime
from main_marts.fct_daily_trading
where fed_funds_rate is not null
order by trading_date, ticker
