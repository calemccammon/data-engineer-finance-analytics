-- Staging model: Clean and standardize company metadata
-- Source: Yahoo Finance company info endpoint
-- Grain: One row per company

with source as (
    select * from {{ source('raw', 'raw_company_info') }}
),

cleaned as (
    select
        ticker,
        company_name,
        coalesce(sector, 'Unknown') as sector,
        coalesce(industry, 'Unknown') as industry,
        market_cap,
        coalesce(currency, 'USD') as currency,
        exchange,
        coalesce(country, 'Unknown') as country,
        website,
        extracted_at
        
    from source
    where ticker is not null
)

select * from cleaned
