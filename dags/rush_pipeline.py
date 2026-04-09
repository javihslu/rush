"""Rush data pipeline DAGs.

Two DAGs with clear separation of concerns:

  rush_ingestion (scheduled daily at 05:00 UTC):
    - Ingest raw transport departures from SBB (transport.opendata.ch)
    - Ingest raw weather forecast from Open-Meteo
    - Trigger the transformation DAG on success

  rush_transformation (triggered by ingestion or manually):
    - Run dbt staging models (clean, type, derive)
    - Run dbt mart models (join, score, recommend)
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
# DAG 1: Ingestion — fetch raw data from APIs into PostgreSQL
# ---------------------------------------------------------------------------

with DAG(
    dag_id="rush_ingestion",
    default_args=default_args,
    description="Ingest raw transport and weather data into PostgreSQL",
    schedule="0 5 * * *",
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=["rush", "ingestion"],
) as ingestion_dag:

    ingest_transport = BashOperator(
        task_id="ingest_transport",
        bash_command="cd /app && uv run python pipelines/ingestion/transport.py",
    )

    ingest_weather = BashOperator(
        task_id="ingest_weather",
        bash_command="cd /app && uv run python pipelines/ingestion/weather.py",
    )

    trigger_transform = TriggerDagRunOperator(
        task_id="trigger_transformation",
        trigger_dag_id="rush_transformation",
        wait_for_completion=False,
    )

    [ingest_transport, ingest_weather] >> trigger_transform


# ---------------------------------------------------------------------------
# DAG 2: Transformation — dbt staging + mart models
# ---------------------------------------------------------------------------

with DAG(
    dag_id="rush_transformation",
    default_args=default_args,
    description="Run dbt transformations: staging views and mart tables",
    schedule=None,  # triggered by ingestion DAG or manually
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=["rush", "transformation"],
) as transformation_dag:

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd /app && uv run dbt run"
            " --project-dir pipelines/transformation/dbt"
            " --profiles-dir pipelines/transformation/dbt"
        ),
    )
