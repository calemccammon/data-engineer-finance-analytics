"""Dagster Definitions — the single entry point for this project.

`dagster dev` auto-discovers this file. It wires together all assets,
jobs, schedules, and resources so Dagster knows about the full pipeline.

Usage:
    dagster dev -m orchestrate -p 3001   # Start the local UI at http://localhost:3001
    dagster asset materialize --select raw_stock_prices   # Materialize one asset
    dagster job execute -j full_pipeline                  # Run the full pipeline
"""

from dagster import Definitions

from orchestrate.assets import (
    dbt_intermediate,
    dbt_marts,
    dbt_seeds,
    dbt_staging,
    dbt_tests,
    raw_tables,
    raw_company_info,
    raw_economic_indicators,
    raw_stock_prices,
)
from orchestrate.jobs import full_pipeline_job, ingest_only_job, transform_only_job
from orchestrate.schedules import daily_pipeline_schedule, weekly_transform_schedule

defs = Definitions(
    assets=[
        raw_stock_prices,
        raw_company_info,
        raw_economic_indicators,
        raw_tables,
        dbt_seeds,
        dbt_staging,
        dbt_intermediate,
        dbt_marts,
        dbt_tests,
    ],
    jobs=[
        full_pipeline_job,
        ingest_only_job,
        transform_only_job,
    ],
    schedules=[
        daily_pipeline_schedule,
        weekly_transform_schedule,
    ],
)
