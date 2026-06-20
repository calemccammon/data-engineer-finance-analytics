-- Intermediate model: Daily return calculations per ticker
-- Grain: One row per ticker per trading day
-- Computes simple daily return and log return for statistical analysis

with prices as (
    select * from {{ ref('stg_stock_prices') }}
),

with_returns as (
    select
        price_id,
        ticker,
        trading_date,
        close_price,
        open_price,
        volume,

        -- Previous trading day close (partition by ticker to avoid cross-ticker lag)
        lag(close_price) over (
            partition by ticker
            order by trading_date
        ) as prev_close_price,

        -- Simple daily return: (close - prev_close) / prev_close
        round(
            (close_price - lag(close_price) over (partition by ticker order by trading_date))
            / nullif(lag(close_price) over (partition by ticker order by trading_date), 0)
            * 100,
            4
        ) as daily_return_pct,

        -- Log return: ln(close / prev_close) — better for statistical aggregation
        round(
            ln(
                close_price
                / nullif(lag(close_price) over (partition by ticker order by trading_date), 0)
            ) * 100,
            4
        ) as log_return_pct,

        -- Overnight gap: open vs previous close
        round(
            (open_price - lag(close_price) over (partition by ticker order by trading_date))
            / nullif(lag(close_price) over (partition by ticker order by trading_date), 0)
            * 100,
            4
        ) as overnight_gap_pct

    from prices
)

select * from with_returns
