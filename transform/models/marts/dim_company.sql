-- Dimension table: Company reference data
-- Grain: One row per company / ticker
-- Source: stg_company_info

with companies as (
    select * from {{ ref('stg_company_info') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['ticker']) }} as company_key,
        ticker,
        company_name,
        sector,
        industry,
        market_cap,
        -- Bucket companies by market cap for easy filtering
        case
            when market_cap >= 1000000000000 then 'Mega Cap (>$1T)'
            when market_cap >= 200000000000  then 'Large Cap ($200B–$1T)'
            when market_cap >= 10000000000   then 'Mid Cap ($10B–$200B)'
            when market_cap >= 2000000000    then 'Small Cap ($2B–$10B)'
            when market_cap is not null          then 'Micro Cap (<$2B)'
            else 'Unknown'
        end as market_cap_category,
        currency,
        exchange,
        country,
        website,
        extracted_at
    from companies
)

select * from final
