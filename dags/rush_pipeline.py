"""Rush data pipeline DAG.

Runs daily at 05:00 UTC:
  1. Ingest transport departures from SBB (transport.opendata.ch)
  2. Ingest weather forecast from Open-Meteo
  3. Run dbt transformations to produce mart_departure_recommendations

Ingestion tasks run in parallel, dbt runs after both complete.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "rush",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="rush_pipeline",
    default_args=default_args,
    description="Full Rush data pipeline: ingest transport + weather, then dbt transform",
    schedule="0 5 * * *",
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=["rush", "ingestion", "transformation"],
) as dag:

    ingest_transport = BashOperator(
        task_id="ingest_transport",
        bash_command="uv run python /app/pipelines/ingestion/transport.py",
    )

    ingest_weather = BashOperator(
        task_id="ingest_weather",
        bash_command="uv run python /app/pipelines/ingestion/weather.py",
    )

    transform = BashOperator(
        task_id="dbt_transform",
        bash_command=(
            "uv run dbt run"
            " --project-dir /app/pipelines/transformation/dbt"
            " --profiles-dir /app/pipelines/transformation/dbt"
        ),
    )

    [ingest_transport, ingest_weather] >> transform
