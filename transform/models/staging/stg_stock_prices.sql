-- Staging model: Clean and standardize raw stock price data
-- Source: Yahoo Finance via yfinance library
-- Grain: One row per ticker per trading day

with source as (
    select * from {{ source('raw', 'raw_stock_prices') }}
),

renamed as (
    select
        -- Create a surrogate key from ticker + date
        {{ dbt_utils.generate_surrogate_key(['ticker', 'date']) }} as price_id,
        
        -- Dimensions
        ticker,
        cast(date as date) as trading_date,
        
        -- Measures: rename to be explicit about what each price represents
        round(open, 4) as open_price,
        round(high, 4) as high_price,
        round(low, 4) as low_price,
        round(close, 4) as close_price,
        volume,
        
        -- Calculated fields
        round(high - low, 4) as intraday_range,
        round((close - open) / nullif(open, 0) * 100, 4) as intraday_return_pct,
        
        -- Metadata
        extracted_at
        
    from source
    where date is not null
      and close is not null
      and volume > 0
)

select * from renamed
