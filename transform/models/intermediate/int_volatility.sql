-- Intermediate model: Rolling volatility metrics
-- Grain: One row per ticker per trading day
-- Volatility is the annualized standard deviation of daily log returns — a key
-- risk metric used in portfolio construction, options pricing, and Sharpe ratios.

with returns as (
    select * from {{ ref('int_daily_returns') }}
),

prices as (
    select price_id, high_price, low_price
    from {{ ref('stg_stock_prices') }}
),

joined as (
    select
        r.price_id,
        r.ticker,
        r.trading_date,
        r.close_price,
        r.daily_return_pct,
        r.log_return_pct,
        round((p.high_price - p.low_price) / nullif(r.close_price, 0) * 100, 4) as intraday_range_pct
    from returns r
    left join prices p on r.price_id = p.price_id
),

with_volatility as (
    select
        price_id,
        ticker,
        trading_date,
        close_price,
        daily_return_pct,
        log_return_pct,

        -- Rolling 20-day realized volatility (annualized)
        -- stddev of log returns * sqrt(252 trading days per year) * 100 → percentage
        round(
            stddev(log_return_pct / 100) over (
                partition by ticker
                order by trading_date
                rows between 19 preceding and current row
            ) * sqrt(252) * 100,
            4
        ) as volatility_20d_annualized,

        -- Rolling 60-day realized volatility
        round(
            stddev(log_return_pct / 100) over (
                partition by ticker
                order by trading_date
                rows between 59 preceding and current row
            ) * sqrt(252) * 100,
            4
        ) as volatility_60d_annualized,

        -- High–Low daily range as a fraction of close (intraday volatility proxy), 20-day average
        round(
            avg(intraday_range_pct) over (
                partition by ticker
                order by trading_date
                rows between 19 preceding and current row
            ),
            4
        ) as avg_intraday_range_pct_20d

    from joined
)

select * from with_volatility
