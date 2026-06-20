"""Dagster job definitions for the Finance Analytics Pipeline.

A job is a named, executable subset of the asset graph. Defining jobs
lets you trigger specific pipeline stages independently — useful for
backfills, debugging, or running just the dbt layer after a model change.
"""

from dagster import AssetSelection, define_asset_job

# Run the full pipeline end-to-end: Extract → Load → dbt
full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=AssetSelection.all(),
    description="Full ELT pipeline: extract from Yahoo Finance, load to DuckDB, run all dbt models.",
)

# Extract + Load only (useful when testing ingestion without running dbt)
ingest_only_job = define_asset_job(
    name="ingest_only",
    selection=AssetSelection.groups("extract", "load"),
    description="Extract raw data and load into DuckDB. Skips dbt transformations.",
)

# dbt only (useful after editing models — data already loaded)
transform_only_job = define_asset_job(
    name="transform_only",
    selection=AssetSelection.groups("dbt"),
    description="Run all dbt models. Assumes raw data is already in DuckDB.",
)
