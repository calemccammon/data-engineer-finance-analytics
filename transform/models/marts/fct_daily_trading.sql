-- Fact table: Daily trading activity — the primary analytical table
-- Grain: One row per ticker per trading day
--
-- Assembles data from:
--   • int_daily_returns   — daily/log returns, overnight gap, prev close
--   • int_moving_averages — SMA 7/30/90/200d, volume signals, 52-week range
--   • int_volatility      — realized volatility (20d, 60d annualized)
--   • int_macro_context   — FRED macro indicators aligned to trading dates
--   • stg_company_info    — sector / industry for slicing & dicing

with returns as (
    select * from {{ ref('int_daily_returns') }}
),

moving_avgs as (
    select * from {{ ref('int_moving_averages') }}
),

volatility as (
    select * from {{ ref('int_volatility') }}
),

macro as (
    select * from {{ ref('int_macro_context') }}
),

companies as (
    select * from {{ ref('stg_company_info') }}
),

enriched as (
    select
        r.price_id,
        r.ticker,
        r.trading_date,

        -- Price data
        r.open_price,
        r.close_price,
        r.prev_close_price,

        -- Return metrics
        r.daily_return_pct,
        r.log_return_pct,
        r.overnight_gap_pct,

        -- Moving averages & momentum signals
        m.sma_7d,
        m.sma_30d,
        m.sma_90d,
        m.sma_200d,
        m.volume,
        m.avg_volume_20d,
        m.avg_volume_90d,
        m.relative_volume_20d,
        m.high_52w,
        m.low_52w,
        m.price_position_52w,

        -- Volatility
        v.volatility_20d_annualized,
        v.volatility_60d_annualized,
        v.avg_intraday_range_pct_20d,

        -- Macro context (forward-filled FRED data)
        mac.fed_funds_rate,
        mac.cpi,
        mac.unemployment_rate,
        mac.treasury_yield_10y,
        mac.gdp_growth_rate,
        mac.breakeven_inflation_10y,
        mac.real_yield_10y,

        -- Company dimensions
        c.company_name,
        c.sector,
        c.industry

    from returns r
    left join moving_avgs m  on r.price_id       = m.price_id
    left join volatility v   on r.price_id       = v.price_id
    left join macro mac      on r.trading_date   = mac.calendar_date
    left join companies c    on r.ticker         = c.ticker
)

select * from enriched
