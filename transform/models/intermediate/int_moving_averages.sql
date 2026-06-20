-- Intermediate model: Rolling moving averages on close price and volume
-- Grain: One row per ticker per trading day
-- Commonly used signals in technical analysis and momentum strategies

with prices as (
    select * from {{ ref('stg_stock_prices') }}
),

with_moving_averages as (
    select
        price_id,
        ticker,
        trading_date,
        close_price,
        volume,

        -- Simple Moving Averages (SMA) on closing price
        round(avg(close_price) over (
            partition by ticker
            order by trading_date
            rows between 6 preceding and current row
        ), 4) as sma_7d,

        round(avg(close_price) over (
            partition by ticker
            order by trading_date
            rows between 29 preceding and current row
        ), 4) as sma_30d,

        round(avg(close_price) over (
            partition by ticker
            order by trading_date
            rows between 89 preceding and current row
        ), 4) as sma_90d,

        round(avg(close_price) over (
            partition by ticker
            order by trading_date
            rows between 199 preceding and current row
        ), 4) as sma_200d,

        -- Rolling volume averages (useful for detecting unusual activity)
        round(avg(volume) over (
            partition by ticker
            order by trading_date
            rows between 19 preceding and current row
        ), 0) as avg_volume_20d,

        round(avg(volume) over (
            partition by ticker
            order by trading_date
            rows between 89 preceding and current row
        ), 0) as avg_volume_90d,

        -- Relative volume: today vs 20-day average (>1 means above-average activity)
        round(
            volume / nullif(avg(volume) over (
                partition by ticker
                order by trading_date
                rows between 20 preceding and 1 preceding
            ), 0),
            2
        ) as relative_volume_20d,

        -- 52-week high / low
        max(close_price) over (
            partition by ticker
            order by trading_date
            rows between 251 preceding and current row
        ) as high_52w,

        min(close_price) over (
            partition by ticker
            order by trading_date
            rows between 251 preceding and current row
        ) as low_52w,

        -- Price position within 52-week range (0 = at low, 1 = at high)
        round(
            (close_price - min(close_price) over (
                partition by ticker
                order by trading_date
                rows between 251 preceding and current row
            ))
            / nullif(
                max(close_price) over (
                    partition by ticker
                    order by trading_date
                    rows between 251 preceding and current row
                )
                - min(close_price) over (
                    partition by ticker
                    order by trading_date
                    rows between 251 preceding and current row
                ),
                0
            ),
            4
        ) as price_position_52w

    from prices
)

select * from with_moving_averages
