-- Staging model: Clean and standardize raw FRED economic indicator data
-- Source: FRED API via fredapi Python library
-- Grain: One row per (series_id, observation_date)
--
-- FRED series included:
--   FEDFUNDS  — Federal Funds Rate (monthly)
--   CPIAUCSL  — Consumer Price Index (monthly)
--   UNRATE    — Unemployment Rate (monthly)
--   DGS10     — 10-Year Treasury Yield (daily)
--   A191RL1Q225SBEA — Real GDP Growth Rate (quarterly)
--   T10YIE    — 10-Year Breakeven Inflation Rate (daily)

with source as (
    select * from {{ source('raw', 'raw_economic_indicators') }}
),

cleaned as (
    select
        series_id,
        series_name,
        cast(observation_date as date) as observation_date,
        cast(value as {{ dbt.type_float() }}) as value,
        frequency,
        extracted_at

    from source
    where observation_date is not null
      and value is not null          -- FRED uses null for missing observations
)

select * from cleaned
