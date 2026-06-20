"""Load raw Parquet files into BigQuery.

This module mirrors load/loader.py but targets Google BigQuery instead of DuckDB.
It is the cloud equivalent of the local loading layer — swap this in to move
the pipeline from local development to production.

Prerequisites
─────────────
1. Install the BigQuery client:
       uv add google-cloud-bigquery google-cloud-bigquery-storage pyarrow

2. Create a GCP service account with roles:
       - BigQuery Data Editor
       - BigQuery Job User

3. Authenticate:
       export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   Or use Application Default Credentials (ADC) via:
       gcloud auth application-default login

4. Set environment variables (or add to .env):
       BQ_PROJECT=your-gcp-project-id

Usage
─────
    from load.bigquery_loader import load_to_bigquery
    load_to_bigquery()

Schema mapping
──────────────
  DuckDB: raw.raw_stock_prices       →  BigQuery: raw.raw_stock_prices
  DuckDB: raw.raw_company_info       →  BigQuery: raw.raw_company_info
  DuckDB: raw.raw_economic_indicators→  BigQuery: raw.raw_economic_indicators
"""

import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("data/raw")


def _get_bq_client():
    """Return an authenticated BigQuery client using the service account keyfile."""
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
    except ImportError as e:
        raise ImportError(
            "google-cloud-bigquery is not installed. Run: uv add google-cloud-bigquery pyarrow"
        ) from e

    project = os.environ.get("BQ_PROJECT")
    if not project:
        raise EnvironmentError(
            "BQ_PROJECT environment variable is required. "
            "Set it in your .env file: BQ_PROJECT=your-project-id"
        )

    keyfile = os.environ.get("BQ_KEYFILE")
    if keyfile:
        credentials = service_account.Credentials.from_service_account_file(
            keyfile,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(project=project, credentials=credentials)

    # Fall back to Application Default Credentials (useful in CI/cloud environments)
    return bigquery.Client(project=project)


def _load_parquet_to_bq(client, df: pd.DataFrame, dataset: str, table: str) -> int:
    """Upload a DataFrame to a BigQuery table (replace if exists)."""
    from google.cloud import bigquery

    table_ref = f"{client.project}.{dataset}.{table}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # idempotent
        autodetect=True,
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()  # wait for completion

    loaded = client.get_table(table_ref).num_rows
    logger.info("Loaded %d rows into %s", loaded, table_ref)
    return loaded


def load_to_bigquery(
    raw_dir: Path | None = None,
    dataset_raw: str = "raw",
) -> list[str]:
    """Load all Parquet files from raw directory into BigQuery.

    Creates the raw dataset if it does not exist and loads each file as a
    table, replacing existing data (idempotent — safe to re-run).

    Args:
        raw_dir: Directory containing raw Parquet files. Defaults to data/raw/.
        dataset_raw: BigQuery dataset name for raw tables. Must match the
                     ``schema: raw`` declared in dbt source definitions.
                     Defaults to "raw".

    Returns:
        List of BigQuery table IDs that were loaded.
    """
    from google.cloud import bigquery

    raw_dir = raw_dir or DEFAULT_RAW_DIR

    client = _get_bq_client()
    loaded_tables: list[str] = []

    # Ensure the dataset exists
    dataset_ref = bigquery.Dataset(f"{client.project}.{dataset_raw}")
    dataset_ref.location = "US"
    client.create_dataset(dataset_ref, exists_ok=True)
    logger.info("Using BigQuery dataset: %s.%s", client.project, dataset_raw)

    # Load stock prices
    price_files = sorted(raw_dir.glob("*_prices.parquet"))
    if price_files:
        logger.info("Loading %d stock price file(s)...", len(price_files))
        df = pd.concat([pd.read_parquet(f) for f in price_files], ignore_index=True)
        _load_parquet_to_bq(client, df, dataset_raw, "raw_stock_prices")
        loaded_tables.append(f"{client.project}.{dataset_raw}.raw_stock_prices")

    # Load company info
    company_file = raw_dir / "company_info.parquet"
    if company_file.exists():
        logger.info("Loading company info...")
        df = pd.read_parquet(company_file)
        _load_parquet_to_bq(client, df, dataset_raw, "raw_company_info")
        loaded_tables.append(f"{client.project}.{dataset_raw}.raw_company_info")

    # Load economic indicators (optional)
    indicators_file = raw_dir / "economic_indicators.parquet"
    if indicators_file.exists():
        logger.info("Loading economic indicators...")
        df = pd.read_parquet(indicators_file)
        _load_parquet_to_bq(client, df, dataset_raw, "raw_economic_indicators")
        loaded_tables.append(f"{client.project}.{dataset_raw}.raw_economic_indicators")

    logger.info("BigQuery load complete. Tables loaded: %s", loaded_tables)
    return loaded_tables


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )
    load_to_bigquery()
