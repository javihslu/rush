"""Rush data preview DAGs.

Manual-only DAGs that query and print sample data from each pipeline stage.
Useful for peer review and debugging: trigger from the Airflow UI, then check
the task logs to see the actual data at each layer.

  rush_preview_local: queries PostgreSQL (raw, staging, mart)
  rush_preview_cloud: queries GCS listing + BigQuery (raw, staging, mart)
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "rush",
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
}

# -- SQL queries for local preview (PostgreSQL) -----------------------------

_PG = "docker compose exec -T pgdatabase psql -U root -d rush"

LOCAL_RAW_TRANSPORT = """
echo '=== transport_raw.departures (last 10 rows) ==='
cd /app && uv run python -c "
import psycopg2, os
conn = psycopg2.connect(host='pgdatabase', port=5432, dbname='rush', user='root', password='root')
cur = conn.cursor()
cur.execute('SELECT count(*) FROM transport_raw.departures')
print(f'Total rows: {cur.fetchone()[0]}')
cur.execute('''
    SELECT station, category, line_name, destination,
           departure_scheduled, departure_actual, ingested_at
    FROM transport_raw.departures
    ORDER BY ingested_at DESC, departure_scheduled DESC
    LIMIT 10
''')
cols = [d[0] for d in cur.description]
print(' | '.join(cols))
print('-' * 120)
for row in cur.fetchall():
    print(' | '.join(str(v) for v in row))
conn.close()
"
"""

LOCAL_RAW_WEATHER = """
echo '=== weather_raw.hourly_forecast (first 10 rows) ==='
cd /app && uv run python -c "
import psycopg2
conn = psycopg2.connect(host='pgdatabase', port=5432, dbname='rush', user='root', password='root')
cur = conn.cursor()
cur.execute('SELECT count(*) FROM weather_raw.hourly_forecast')
print(f'Total rows: {cur.fetchone()[0]}')
cur.execute('''
    SELECT forecast_time, temperature_2m, precipitation, snowfall,
           windspeed_10m, weathercode, visibility
    FROM weather_raw.hourly_forecast
    ORDER BY forecast_time
    LIMIT 10
''')
cols = [d[0] for d in cur.description]
print(' | '.join(cols))
print('-' * 100)
for row in cur.fetchall():
    print(' | '.join(str(v) for v in row))
conn.close()
"
"""

LOCAL_STAGING = """
echo '=== dbt_dev.stg_transport__departures (10 rows) ==='
cd /app && uv run python -c "
import psycopg2
conn = psycopg2.connect(host='pgdatabase', port=5432, dbname='rush', user='root', password='root')
cur = conn.cursor()
cur.execute('SELECT count(*) FROM dbt_dev.stg_transport__departures')
print(f'Total rows: {cur.fetchone()[0]}')
cur.execute('''
    SELECT station, category, destination,
           departure_scheduled_at, delay_minutes, is_delayed
    FROM dbt_dev.stg_transport__departures
    ORDER BY departure_scheduled_at DESC
    LIMIT 10
''')
cols = [d[0] for d in cur.description]
print(' | '.join(cols))
print('-' * 100)
for row in cur.fetchall():
    print(' | '.join(str(v) for v in row))
conn.close()
"

echo ''
echo '=== dbt_dev.stg_weather__forecast (10 rows) ==='
cd /app && uv run python -c "
import psycopg2
conn = psycopg2.connect(host='pgdatabase', port=5432, dbname='rush', user='root', password='root')
cur = conn.cursor()
cur.execute('SELECT count(*) FROM dbt_dev.stg_weather__forecast')
print(f'Total rows: {cur.fetchone()[0]}')
cur.execute('''
    SELECT forecast_hour, temperature_2m, precipitation, snowfall,
           weather_condition, bad_weather
    FROM dbt_dev.stg_weather__forecast
    ORDER BY forecast_hour
    LIMIT 10
''')
cols = [d[0] for d in cur.description]
print(' | '.join(cols))
print('-' * 100)
for row in cur.fetchall():
    print(' | '.join(str(v) for v in row))
conn.close()
"
"""

LOCAL_MART = """
echo '=== dbt_dev.mart_departure_recommendations (10 rows) ==='
cd /app && uv run python -c "
import psycopg2
conn = psycopg2.connect(host='pgdatabase', port=5432, dbname='rush', user='root', password='root')
cur = conn.cursor()
cur.execute('SELECT count(*) FROM dbt_dev.mart_departure_recommendations')
print(f'Total rows: {cur.fetchone()[0]}')
cur.execute('''
    SELECT station, category, destination,
           departure_scheduled_at, delay_minutes,
           weather_condition, rush_score, recommendation
    FROM dbt_dev.mart_departure_recommendations
    ORDER BY departure_scheduled_at DESC
    LIMIT 10
''')
cols = [d[0] for d in cur.description]
print(' | '.join(cols))
print('-' * 130)
for row in cur.fetchall():
    print(' | '.join(str(v) for v in row))
conn.close()
"

echo ''
echo '=== Recommendation distribution ==='
cd /app && uv run python -c "
import psycopg2
conn = psycopg2.connect(host='pgdatabase', port=5432, dbname='rush', user='root', password='root')
cur = conn.cursor()
cur.execute('''
    SELECT recommendation, count(*) as cnt,
           round(avg(rush_score)::numeric, 1) as avg_score
    FROM dbt_dev.mart_departure_recommendations
    GROUP BY recommendation
    ORDER BY avg_score
''')
cols = [d[0] for d in cur.description]
print(' | '.join(cols))
print('-' * 40)
for row in cur.fetchall():
    print(' | '.join(str(v) for v in row))
conn.close()
"
"""

# -- SQL queries for cloud preview (BigQuery) -------------------------------

CLOUD_GCS_LISTING = """
echo '=== GCS data lake contents ==='
cd /app && uv run python -c "
import os
from google.cloud import storage
client = storage.Client(project=os.environ.get('GCP_PROJECT_ID'))
bucket = client.bucket(os.environ.get('GCP_BUCKET_NAME'))
blobs = list(bucket.list_blobs(prefix='raw/'))
print(f'Total objects: {len(blobs)}')
print()
for b in sorted(blobs, key=lambda x: x.name):
    ts = b.updated.strftime('%Y-%m-%d %H:%M UTC')
    print(f'  {b.name}  ({b.size:,} bytes, updated {ts})')
"
"""

CLOUD_RAW_BQ = """
echo '=== BigQuery: transport_raw.departures (10 rows) ==='
cd /app && uv run python -c "
import os
from google.cloud import bigquery
client = bigquery.Client(project=os.environ.get('GCP_PROJECT_ID'))
t = client.get_table('transport_raw.departures')
print(f'Total rows: {t.num_rows}')
rows = client.query('''
    SELECT station, category, line_name, destination,
           departure_scheduled, departure_actual, ingested_at
    FROM transport_raw.departures
    ORDER BY ingested_at DESC, departure_scheduled DESC
    LIMIT 10
''').result()
first = True
for row in rows:
    if first:
        print(' | '.join(row.keys()))
        print('-' * 120)
        first = False
    print(' | '.join(str(v) for v in row.values()))
"

echo ''
echo '=== BigQuery: weather_raw.hourly_forecast (10 rows) ==='
cd /app && uv run python -c "
import os
from google.cloud import bigquery
client = bigquery.Client(project=os.environ.get('GCP_PROJECT_ID'))
t = client.get_table('weather_raw.hourly_forecast')
print(f'Total rows: {t.num_rows}')
rows = client.query('''
    SELECT forecast_time, temperature_2m, precipitation, snowfall,
           windspeed_10m, weathercode, visibility
    FROM weather_raw.hourly_forecast
    ORDER BY forecast_time
    LIMIT 10
''').result()
first = True
for row in rows:
    if first:
        print(' | '.join(row.keys()))
        print('-' * 100)
        first = False
    print(' | '.join(str(v) for v in row.values()))
"
"""

CLOUD_STAGING_BQ = """
echo '=== BigQuery: rush.stg_transport__departures (10 rows) ==='
cd /app && uv run python -c "
import os
from google.cloud import bigquery
client = bigquery.Client(project=os.environ.get('GCP_PROJECT_ID'))
rows = client.query('''
    SELECT station, category, destination,
           departure_scheduled_at, delay_minutes, is_delayed
    FROM rush.stg_transport__departures
    ORDER BY departure_scheduled_at DESC
    LIMIT 10
''').result()
first = True
for row in rows:
    if first:
        print(' | '.join(row.keys()))
        print('-' * 100)
        first = False
    print(' | '.join(str(v) for v in row.values()))
"

echo ''
echo '=== BigQuery: rush.stg_weather__forecast (10 rows) ==='
cd /app && uv run python -c "
import os
from google.cloud import bigquery
client = bigquery.Client(project=os.environ.get('GCP_PROJECT_ID'))
rows = client.query('''
    SELECT forecast_hour, temperature_2m, precipitation, snowfall,
           weather_condition, bad_weather
    FROM rush.stg_weather__forecast
    ORDER BY forecast_hour
    LIMIT 10
''').result()
first = True
for row in rows:
    if first:
        print(' | '.join(row.keys()))
        print('-' * 100)
        first = False
    print(' | '.join(str(v) for v in row.values()))
"
"""

CLOUD_MART_BQ = """
echo '=== BigQuery: rush.mart_departure_recommendations (10 rows) ==='
cd /app && uv run python -c "
import os
from google.cloud import bigquery
client = bigquery.Client(project=os.environ.get('GCP_PROJECT_ID'))
t = client.get_table('rush.mart_departure_recommendations')
print(f'Total rows: {t.num_rows}')
rows = client.query('''
    SELECT station, category, destination,
           departure_scheduled_at, delay_minutes,
           weather_condition, rush_score, recommendation
    FROM rush.mart_departure_recommendations
    ORDER BY departure_scheduled_at DESC
    LIMIT 10
''').result()
first = True
for row in rows:
    if first:
        print(' | '.join(row.keys()))
        print('-' * 130)
        first = False
    print(' | '.join(str(v) for v in row.values()))
"

echo ''
echo '=== Recommendation distribution ==='
cd /app && uv run python -c "
import os
from google.cloud import bigquery
client = bigquery.Client(project=os.environ.get('GCP_PROJECT_ID'))
rows = client.query('''
    SELECT recommendation, count(*) as cnt,
           round(avg(rush_score), 1) as avg_score
    FROM rush.mart_departure_recommendations
    GROUP BY recommendation
    ORDER BY avg_score
''').result()
first = True
for row in rows:
    if first:
        print(' | '.join(row.keys()))
        print('-' * 40)
        first = False
    print(' | '.join(str(v) for v in row.values()))
"
"""


# ---------------------------------------------------------------------------
# DAG 5: Local Data Preview — inspect PostgreSQL at every stage
# ---------------------------------------------------------------------------

with DAG(
    dag_id="rush_preview_local",
    default_args=default_args,
    description="Preview data at each local pipeline stage (PostgreSQL)",
    schedule=None,
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=["rush", "preview"],
) as local_preview_dag:

    raw_transport = BashOperator(
        task_id="raw_transport",
        bash_command=LOCAL_RAW_TRANSPORT,
    )

    raw_weather = BashOperator(
        task_id="raw_weather",
        bash_command=LOCAL_RAW_WEATHER,
    )

    staging = BashOperator(
        task_id="staging_models",
        bash_command=LOCAL_STAGING,
    )

    mart = BashOperator(
        task_id="mart_recommendations",
        bash_command=LOCAL_MART,
    )

    [raw_transport, raw_weather] >> staging >> mart


# ---------------------------------------------------------------------------
# DAG 6: Cloud Data Preview — inspect GCS + BigQuery at every stage
# ---------------------------------------------------------------------------

with DAG(
    dag_id="rush_preview_cloud",
    default_args=default_args,
    description="Preview data at each cloud pipeline stage (GCS + BigQuery)",
    schedule=None,
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=["rush", "cloud", "preview"],
) as cloud_preview_dag:

    gcs_listing = BashOperator(
        task_id="gcs_data_lake",
        bash_command=CLOUD_GCS_LISTING,
    )

    raw_bq = BashOperator(
        task_id="raw_bigquery",
        bash_command=CLOUD_RAW_BQ,
    )

    staging_bq = BashOperator(
        task_id="staging_bigquery",
        bash_command=CLOUD_STAGING_BQ,
    )

    mart_bq = BashOperator(
        task_id="mart_bigquery",
        bash_command=CLOUD_MART_BQ,
    )

    gcs_listing >> raw_bq >> staging_bq >> mart_bq
