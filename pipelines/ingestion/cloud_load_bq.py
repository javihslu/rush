"""Load raw data from GCS into BigQuery datasets.

Creates BigQuery datasets and loads newline-delimited JSON files
from the data lake into raw tables. Run after cloud_upload.py:

    docker compose exec dev uv run python pipelines/ingestion/cloud_load_bq.py
"""

from __future__ import annotations

import os
import sys

from google.cloud import bigquery


def load_gcs_to_bq(
    client: bigquery.Client,
    bucket_name: str,
    blob_path: str,
    dataset_id: str,
    table_id: str,
    write_disposition: str = "WRITE_TRUNCATE",
) -> int:
    """Load a GCS JSON file into a BigQuery table with auto-detected schema.

    Args:
        client:            BigQuery client.
        bucket_name:       GCS bucket name.
        blob_path:         Path to the JSON file in the bucket.
        dataset_id:        BigQuery dataset name.
        table_id:          BigQuery table name.
        write_disposition: WRITE_TRUNCATE or WRITE_APPEND.

    Returns:
        Number of rows loaded.
    """
    dataset_ref = bigquery.DatasetReference(client.project, dataset_id)

    # Ensure dataset exists
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "europe-west6"
        client.create_dataset(dataset)
        print(f"  Created dataset: {dataset_id}")

    table_ref = dataset_ref.table(table_id)
    uri = f"gs://{bucket_name}/{blob_path}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
        write_disposition=write_disposition,
    )

    load_job = client.load_table_from_uri(uri, table_ref, job_config=job_config)
    load_job.result()  # Wait for completion

    table = client.get_table(table_ref)
    print(f"  Loaded {table.num_rows} rows into {dataset_id}.{table_id}")
    return table.num_rows


def main() -> None:
    """Load transport and weather data from GCS into BigQuery."""
    project_id = os.environ.get("GCP_PROJECT_ID")
    bucket_name = os.environ.get("GCP_BUCKET_NAME")

    if not project_id or not bucket_name:
        print("ERROR: GCP_PROJECT_ID and GCP_BUCKET_NAME must be set.")
        sys.exit(1)

    client = bigquery.Client(project=project_id)

    from datetime import datetime, timezone

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("Loading transport data into BigQuery ...")
    load_gcs_to_bq(
        client,
        bucket_name,
        f"raw/transport/departures_{date_str}.json",
        "transport_raw",
        "departures",
        write_disposition="WRITE_APPEND",
    )

    print("Loading weather data into BigQuery ...")
    load_gcs_to_bq(
        client,
        bucket_name,
        f"raw/weather/forecast_{date_str}.json",
        "weather_raw",
        "hourly_forecast",
        write_disposition="WRITE_TRUNCATE",
    )

    print("BigQuery load complete.")


if __name__ == "__main__":
    main()
