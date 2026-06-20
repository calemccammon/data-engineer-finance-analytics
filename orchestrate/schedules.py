"""Dagster schedule definitions for the Finance Analytics Pipeline.

Schedules use cron syntax. Stock market data updates after market close,
so a daily run at 6:00 PM ET (23:00 UTC) gives the exchange time to
settle final prices before we pull them.

Cron cheatsheet:
    "0 23 * * 1-5"   → 11pm UTC, Monday–Friday
    "0 23 * * *"     → 11pm UTC, every day (includes weekends — yfinance handles no-data days gracefully)
"""

from dagster import ScheduleDefinition

from orchestrate.jobs import full_pipeline_job, transform_only_job

# Primary schedule: full pipeline on weekday evenings
daily_pipeline_schedule = ScheduleDefinition(
    name="daily_pipeline_schedule",
    job=full_pipeline_job,
    cron_schedule="0 23 * * 1-5",  # 11pm UTC = 7pm ET (accounts for DST buffer)
    description="Run the full ELT pipeline Monday–Friday after US market close.",
)

# Weekly dbt-only refresh — run every Saturday to catch any seed/macro updates
# without pulling fresh market data.
weekly_transform_schedule = ScheduleDefinition(
    name="weekly_transform_schedule",
    job=transform_only_job,
    cron_schedule="0 8 * * 6",  # 8am UTC Saturday
    description="Re-run all dbt models on Saturday to apply any model changes.",
)
