-- Custom test: Every ticker in the fact table must exist in dim_company
-- Detects orphaned fact rows that would produce NULLs in sector/industry
-- columns when analysts slice the mart.

select distinct
    f.ticker
from {{ ref('fct_daily_trading') }} f
left join {{ ref('stg_company_info') }} c
    on f.ticker = c.ticker
where c.ticker is null
