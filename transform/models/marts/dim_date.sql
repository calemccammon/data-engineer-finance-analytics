-- Dimension table: Calendar / date spine
-- Grain: One row per calendar day from the earliest to latest trading date in the dataset
-- Provides rich date attributes for time-series analysis
-- Compatible with DuckDB (local) and BigQuery (cloud).

with date_spine as (
    {{
        dbt_utils.date_spine(
            datepart="day",
            start_date="cast('2020-01-01' as date)",
            end_date="cast('2028-01-01' as date)"
        )
    }}
),

trading_dates as (
    select distinct trading_date
    from {{ ref('stg_stock_prices') }}
),

calendar as (
    select
        cast(d.date_day as date) as calendar_date,

        -- Basic date parts (standard SQL — works on both)
        cast(extract(year    from d.date_day) as int64) as year,
        cast(extract(month   from d.date_day) as int64) as month_num,
        cast(extract(day     from d.date_day) as int64) as day_of_month,
        cast(extract(quarter from d.date_day) as int64) as quarter_num,

        -- Day of week (0=Sunday): DuckDB DOW vs BigQuery DAYOFWEEK (1=Sunday)
        {% if target.type == 'bigquery' %}
        cast(extract(dayofweek from d.date_day) - 1 as int64) as day_of_week,
        cast(extract(dayofyear from d.date_day)     as int64) as day_of_year,
        cast(extract(week      from d.date_day)     as int64) as week_of_year,
        {% else %}
        cast(extract(dow from d.date_day) as integer) as day_of_week,
        cast(extract(doy from d.date_day) as integer) as day_of_year,
        cast(extract(week from d.date_day) as integer) as week_of_year,
        {% endif %}

        -- Friendly labels (adapter-specific format functions)
        {% if target.type == 'bigquery' %}
        format_date('%B', cast(d.date_day as date)) as month_name,
        format_date('%b', cast(d.date_day as date)) as month_name_short,
        format_date('%A', cast(d.date_day as date)) as day_name,
        format_date('%a', cast(d.date_day as date)) as day_name_short,
        {% else %}
        strftime(d.date_day, '%B') as month_name,
        strftime(d.date_day, '%b') as month_name_short,
        strftime(d.date_day, '%A') as day_name,
        strftime(d.date_day, '%a') as day_name_short,
        {% endif %}

        -- Period keys for aggregations
        {% if target.type == 'bigquery' %}
        cast(format_date('%Y%m', cast(d.date_day as date)) as int64) as year_month_key,
        cast(format_date('%Y',   cast(d.date_day as date)) as int64) as year_key,
        cast(concat(
            cast(extract(year    from d.date_day) as string), '-Q',
            cast(extract(quarter from d.date_day) as string)
        ) as string) as fiscal_quarter_label,
        {% else %}
        cast(strftime(d.date_day, '%Y%m') as integer) as year_month_key,
        cast(strftime(d.date_day, '%Y')   as integer) as year_key,
        cast(extract(year from d.date_day) as integer) || '-Q' ||
            cast(extract(quarter from d.date_day) as integer) as fiscal_quarter_label,
        {% endif %}

        -- Weekend / weekday flag
        case when extract(
            {% if target.type == 'bigquery' %}dayofweek{% else %}dow{% endif %}
            from d.date_day) in ({% if target.type == 'bigquery' %}1, 7{% else %}0, 6{% endif %})
             then true else false
        end as is_weekend,

        -- Trading day flag
        case when t.trading_date is not null then true else false end as is_trading_day,

        -- Relative flags
        case when cast(d.date_day as date) = current_date then true else false end as is_today,
        case when extract(year from d.date_day) = extract(year from current_date)
             then true else false end as is_current_year,
        {% if target.type == 'bigquery' %}
        case when format_date('%Y%m', cast(d.date_day as date))
                  = format_date('%Y%m', current_date)
             then true else false end as is_current_month
        {% else %}
        case when cast(strftime(d.date_day, '%Y%m') as integer)
                  = cast(strftime(current_date, '%Y%m') as integer)
             then true else false end as is_current_month
        {% endif %}

    from date_spine d
    left join trading_dates t
        on cast(d.date_day as date) = t.trading_date
)

select * from calendar

