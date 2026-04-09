"""Rush cloud pipeline DAGs.

Two DAGs for the GCP cloud pipeline:

  rush_cloud_ingestion (triggered manually or scheduled):
    - Fetch raw data from APIs and upload to GCS data lake
    - Trigger the cloud transformation DAG on success

  rush_cloud_transformation (triggered by ingestion or manually):
    - Run dbt with --target prod to transform data in BigQuery
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

default_args = {
    "owner": "rush",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ---------------------------------------------------------------------------
# DAG 3: Cloud Ingestion — fetch raw data from APIs and upload to GCS
# ---------------------------------------------------------------------------

with DAG(
    dag_id="rush_cloud_ingestion",
    default_args=default_args,
    description="Upload raw transport and weather data to GCS data lake",
    schedule=None,
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=["rush", "cloud", "ingestion"],
) as cloud_ingestion_dag:

    cloud_upload = BashOperator(
        task_id="upload_to_gcs",
        bash_command="cd /app && uv run python pipelines/ingestion/cloud_upload.py",
    )

    load_to_bq = BashOperator(
        task_id="load_gcs_to_bigquery",
        bash_command="cd /app && uv run python pipelines/ingestion/cloud_load_bq.py",
    )

    trigger_cloud_transform = TriggerDagRunOperator(
        task_id="trigger_cloud_transformation",
        trigger_dag_id="rush_cloud_transformation",
        wait_for_completion=False,
    )

    cloud_upload >> load_to_bq >> trigger_cloud_transform


# ---------------------------------------------------------------------------
# DAG 4: Cloud Transformation — dbt to BigQuery
# ---------------------------------------------------------------------------

with DAG(
    dag_id="rush_cloud_transformation",
    default_args=default_args,
    description="Run dbt transformations against BigQuery (prod target)",
    schedule=None,
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=["rush", "cloud", "transformation"],
) as cloud_transformation_dag:

    dbt_run_prod = BashOperator(
        task_id="dbt_run_prod",
        bash_command=(
            "cd /app && uv run dbt run"
            " --project-dir pipelines/transformation/dbt"
            " --profiles-dir pipelines/transformation/dbt"
            " --target prod"
        ),
    )
