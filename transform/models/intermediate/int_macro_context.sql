-- Intermediate model: Macro context aligned to trading dates
-- Grain: One row per trading date
--
-- Problem: FRED data is mixed-frequency (daily, monthly, quarterly), and a
-- monthly or quarterly figure is dated by the period it describes, not the day
-- it was published. March's CPI is dated 1 March and comes out in mid-April.
--
-- Solution: each observation is moved to the date it became public, and each
-- trading date takes the latest value public by then. The value stands until
-- the next one is released: a rate set for one month is still the latest known
-- rate two weeks into the next.
--
-- Two things this guards against:
--   * Using a figure before anyone could have known it.
--   * Losing an observation because its date is not a trading day. The first of
--     a month is often a weekend, and 1 January never trades. The observations
--     and the trading dates are laid on one timeline, so no observation has to
--     match a trading date to be carried forward.

{% set release_lag_days = var('fred_release_lag_days') %}

with indicators as (
    select * from {{ ref('stg_economic_indicators') }}
),

-- How long after its observation date each series is published
lagged as (
    select
        series_id,
        observation_date,
        value,
        case series_id
            {%- for series_id, days in release_lag_days.items() %}
            when '{{ series_id }}' then {{ days }}
            {%- endfor %}
            else 0
        end as release_lag_days
    from indicators
),

released as (
    select
        series_id,
        value,
        cast({{ dbt.dateadd('day', 'release_lag_days', 'observation_date') }} as date) as available_date
    from lagged
),

-- Pivot from long format (one row per series per date) to wide format
-- (one row per date, one column per series)
pivoted as (
    select
        available_date,

        max(case when series_id = 'FEDFUNDS'        then value end) as fed_funds_rate,
        max(case when series_id = 'CPIAUCSL'        then value end) as cpi,
        max(case when series_id = 'UNRATE'          then value end) as unemployment_rate,
        max(case when series_id = 'DGS10'           then value end) as treasury_yield_10y,
        max(case when series_id = 'A191RL1Q225SBEA' then value end) as gdp_growth_rate,
        max(case when series_id = 'T10YIE'          then value end) as breakeven_inflation_10y

    from released
    group by available_date
),

trading_dates as (
    select distinct trading_date as calendar_date
    from {{ ref('stg_stock_prices') }}
),

-- One timeline holding every release and every trading date. A release on a
-- trading date sorts before it, so the value is in force that same day.
timeline as (
    select
        available_date as timeline_date,
        0 as is_trading_date,
        fed_funds_rate,
        cpi,
        unemployment_rate,
        treasury_yield_10y,
        gdp_growth_rate,
        breakeven_inflation_10y
    from pivoted

    union all

    select
        calendar_date as timeline_date,
        1 as is_trading_date,
        cast(null as {{ dbt.type_float() }}) as fed_funds_rate,
        cast(null as {{ dbt.type_float() }}) as cpi,
        cast(null as {{ dbt.type_float() }}) as unemployment_rate,
        cast(null as {{ dbt.type_float() }}) as treasury_yield_10y,
        cast(null as {{ dbt.type_float() }}) as gdp_growth_rate,
        cast(null as {{ dbt.type_float() }}) as breakeven_inflation_10y
    from trading_dates
),

-- Carry the latest released value of each series forward along the timeline
forward_filled as (
    select
        timeline_date,
        is_trading_date,
        last_value(fed_funds_rate ignore nulls)          over latest_so_far as fed_funds_rate,
        last_value(cpi ignore nulls)                     over latest_so_far as cpi,
        last_value(unemployment_rate ignore nulls)       over latest_so_far as unemployment_rate,
        last_value(treasury_yield_10y ignore nulls)      over latest_so_far as treasury_yield_10y,
        last_value(gdp_growth_rate ignore nulls)         over latest_so_far as gdp_growth_rate,
        last_value(breakeven_inflation_10y ignore nulls) over latest_so_far as breakeven_inflation_10y
    from timeline
    window latest_so_far as (
        order by timeline_date, is_trading_date
        rows between unbounded preceding and current row
    )
)

select
    timeline_date as calendar_date,
    fed_funds_rate,
    cpi,
    unemployment_rate,
    treasury_yield_10y,
    gdp_growth_rate,
    breakeven_inflation_10y,
    -- Real yield = nominal 10y treasury minus breakeven inflation
    round(treasury_yield_10y - breakeven_inflation_10y, 4) as real_yield_10y
from forward_filled
where is_trading_date = 1
