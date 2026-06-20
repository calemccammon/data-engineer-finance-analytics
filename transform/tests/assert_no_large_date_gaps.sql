-- Custom test: No ticker should have unexpectedly large gaps between trading days
-- We flag any consecutive-day gap > 7 calendar days (covers long weekends and
-- public holidays, but catches genuine missing data).
--
-- Note: this test intentionally ignores the first row per ticker (no prior date).

with ordered as (
    select
        price_id,
        ticker,
        trading_date,
        lag(trading_date) over (
            partition by ticker
            order by trading_date
        ) as prev_trading_date
    from {{ ref('stg_stock_prices') }}
),

gaps as (
    select
        price_id,
        ticker,
        trading_date,
        prev_trading_date,
        {% if target.type == 'bigquery' %}
        date_diff(trading_date, prev_trading_date, day) as gap_days
        {% else %}
        datediff('day', prev_trading_date, trading_date) as gap_days
        {% endif %}
    from ordered
    where prev_trading_date is not null
)

select
    price_id,
    ticker,
    trading_date,
    prev_trading_date,
    gap_days
from gaps
where gap_days > 7
