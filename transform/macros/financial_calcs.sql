{% macro calculate_cagr(start_value, end_value, num_years) %}
    -- Compound Annual Growth Rate: (end/start)^(1/years) - 1
    -- Returns as a decimal (multiply by 100 for percentage)
    (
        power(
            cast({{ end_value }} as double) / nullif(cast({{ start_value }} as double), 0),
            1.0 / nullif({{ num_years }}, 0)
        ) - 1
    )
{% endmacro %}


{% macro calculate_sharpe_ratio(avg_return, risk_free_rate, volatility) %}
    -- Sharpe Ratio: (avg_return - risk_free_rate) / volatility
    -- All inputs should be in the same unit (e.g., all as annualized percentages)
    (
        ({{ avg_return }} - {{ risk_free_rate }})
        / nullif({{ volatility }}, 0)
    )
{% endmacro %}


{% macro calculate_max_drawdown(price_column, ticker_column, date_column) %}
    -- Maximum Drawdown: largest peak-to-trough decline as a percentage
    -- Returns a value between -1 (100% loss) and 0 (no drawdown)
    round(
        (
            {{ price_column }}
            / nullif(
                max({{ price_column }}) over (
                    partition by {{ ticker_column }}
                    order by {{ date_column }}
                    rows between unbounded preceding and current row
                ),
                0
            )
        ) - 1,
        4
    )
{% endmacro %}


{% macro pct_change(current_value, prior_value) %}
    -- Generic percentage change formula with null-safety
    round(
        (cast({{ current_value }} as double) - cast({{ prior_value }} as double))
        / nullif(cast({{ prior_value }} as double), 0)
        * 100,
        4
    )
{% endmacro %}
