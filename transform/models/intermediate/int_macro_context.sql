-- Intermediate model: Macro context aligned to daily trading dates
-- Grain: One row per calendar date (within our trading data range)
--
-- Problem: FRED data is mixed-frequency (daily, monthly, quarterly).
-- Solution: Forward-fill each series to produce a value for every calendar
-- date, so it can be joined to fct_daily_trading on trading_date.
--
-- Forward-fill is the correct approach for macro data: a Fed Funds Rate
-- set on the 1st of the month is still valid on the 15th — the rate
-- hasn't changed just because no new observation was published.

with indicators as (
    select * from {{ ref('stg_economic_indicators') }}
),

-- Pivot from long format (one row per series per date) to wide format
-- (one row per date, one column per series)
pivoted as (
    select
        observation_date,

        max(case when series_id = 'FEDFUNDS'        then value end) as fed_funds_rate,
        max(case when series_id = 'CPIAUCSL'        then value end) as cpi,
        max(case when series_id = 'UNRATE'          then value end) as unemployment_rate,
        max(case when series_id = 'DGS10'           then value end) as treasury_yield_10y,
        max(case when series_id = 'A191RL1Q225SBEA' then value end) as gdp_growth_rate,
        max(case when series_id = 'T10YIE'          then value end) as breakeven_inflation_10y

    from indicators
    group by observation_date
),

-- Build a spine of every calendar date in our trading data range,
-- then left-join macro observations onto it
date_spine as (
    select distinct trading_date as calendar_date
    from {{ ref('stg_stock_prices') }}
),

joined as (
    select
        d.calendar_date,
        p.fed_funds_rate,
        p.cpi,
        p.unemployment_rate,
        p.treasury_yield_10y,
        p.gdp_growth_rate,
        p.breakeven_inflation_10y
    from date_spine d
    left join pivoted p
        on d.calendar_date = p.observation_date
),

-- Forward-fill nulls: carry the last known value forward for each series
forward_filled as (
    select
        calendar_date,

        -- last_value(... ignore nulls) fills each column forward within the date window
        last_value(fed_funds_rate ignore nulls) over (
            order by calendar_date rows between unbounded preceding and current row
        ) as fed_funds_rate,

        last_value(cpi ignore nulls) over (
            order by calendar_date rows between unbounded preceding and current row
        ) as cpi,

        last_value(unemployment_rate ignore nulls) over (
            order by calendar_date rows between unbounded preceding and current row
        ) as unemployment_rate,

        last_value(treasury_yield_10y ignore nulls) over (
            order by calendar_date rows between unbounded preceding and current row
        ) as treasury_yield_10y,

        last_value(gdp_growth_rate ignore nulls) over (
            order by calendar_date rows between unbounded preceding and current row
        ) as gdp_growth_rate,

        last_value(breakeven_inflation_10y ignore nulls) over (
            order by calendar_date rows between unbounded preceding and current row
        ) as breakeven_inflation_10y,

        -- Real yield = nominal 10y treasury minus breakeven inflation
        round(
            last_value(treasury_yield_10y ignore nulls) over (
                order by calendar_date rows between unbounded preceding and current row
            )
            - last_value(breakeven_inflation_10y ignore nulls) over (
                order by calendar_date rows between unbounded preceding and current row
            ),
            4
        ) as real_yield_10y

    from joined
)

select * from forward_filled
