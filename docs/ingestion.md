# 2. Ingestion Pipeline

> **Points: 10** — Provide a Python ingestion script that loads data from the source into storage. Must be batch-based, modular, readable, and documented.

---

## Overview

Rush uses [dlt](https://dlthub.com/) (data load tool) for ingestion. Two independent scripts fetch data from public APIs and load it into PostgreSQL as raw tables. No derived fields are computed during ingestion — the raw data is stored exactly as received from the API, with only structural flattening applied.

```mermaid
flowchart LR
    SBB["transport.opendata.ch"] -->|HTTP GET| TP["transport.py"]
    OME["Open-Meteo API"] -->|HTTP GET| WP["weather.py"]
    TP -->|dlt pipeline| PG["PostgreSQL<br/>transport_raw.departures"]
    WP -->|dlt pipeline| PG2["PostgreSQL<br/>weather_raw.hourly_forecast"]

    style PG fill:#2d333b,stroke:#f0883e
    style PG2 fill:#2d333b,stroke:#79c0ff
```

---

## Transport Ingestion

**Source file:** [`pipelines/ingestion/transport.py`](https://github.com/javihslu/rush/blob/main/pipelines/ingestion/transport.py)

Fetches upcoming departures from the Swiss public transport API for a list of stations (default: Luzern). Each API response is parsed into flat departure records.

**What it stores (raw):**

| Column | Type | Description |
|--------|------|-------------|
| `id` | string | Composite key: station + line number + scheduled time |
| `station` | string | Station name |
| `line_name` | string | Full line identifier (e.g. "IC 8 1516") |
| `category` | string | IC, IR, S, RE, etc. |
| `line_number` | string | Line number (e.g. "1516") |
| `operator` | string | Operating company |
| `destination` | string | Final stop |
| `platform_scheduled` | string | Expected platform |
| `platform_actual` | string | Actual platform (from prognosis, null if unchanged) |
| `departure_scheduled` | string | ISO-8601 timestamp |
| `departure_actual` | string | ISO-8601 timestamp (null if on time) |
| `ingested_at` | string | Batch timestamp |

**Key design decisions:**

- `write_disposition="append"` — each run adds new rows, preserving historical data
- `primary_key="id"` — deduplicates within a batch (same departure fetched twice)
- No delay computation — raw timestamps are stored as strings; delay_minutes is derived in dbt

**dlt resource definition:**

```python
@dlt.resource(name="departures", write_disposition="append", primary_key="id")
def departures_resource(stations: list[str] = None):
    ingested_at = datetime.now(timezone.utc).isoformat()
    for station in (stations or STATIONS):
        raw_list = fetch_stationboard(station)
        for raw in raw_list:
            yield parse_departure(raw, station, ingested_at)
```

---

## Weather Ingestion

**Source file:** [`pipelines/ingestion/weather.py`](https://github.com/javihslu/rush/blob/main/pipelines/ingestion/weather.py)

Fetches a 7-day hourly weather forecast from Open-Meteo for Luzern. The API returns columnar arrays (one array per variable); the script pivots them into flat rows — one row per forecast hour.

**What it stores (raw):**

| Column | Type | Description |
|--------|------|-------------|
| `id` | string | Composite key: lat + lon + forecast_time |
| `forecast_time` | string | Hour in local time |
| `latitude` | float | Location latitude |
| `longitude` | float | Location longitude |
| `temperature_2m` | float | Air temperature (C) |
| `precipitation` | float | Total precipitation (mm) |
| `rain` | float | Liquid rain (mm) |
| `snowfall` | float | Snow accumulation (cm) |
| `windspeed_10m` | float | Wind speed (km/h) |
| `weathercode` | int | WMO weather condition code |
| `visibility` | float | Visibility (m) |
| `ingested_at` | string | Batch timestamp |

**Key design decisions:**

- `write_disposition="replace"` — each run replaces the previous forecast (forecasts are inherently forward-looking; stale data has no value)
- Columnar-to-row pivot is structural, not business transformation — it converts the API format into a relational format that PostgreSQL and BigQuery can query

```python
@dlt.resource(name="hourly_forecast", write_disposition="replace", primary_key="id")
def forecast_resource():
    raw = fetch_forecast()
    ingested_at = datetime.now(timezone.utc).isoformat()
    for record in parse_forecast(raw, ingested_at):
        yield record
```

---

## Batch Design

Both scripts are designed to be run on a schedule (daily at 05:00 UTC via Airflow). They are:

- **Idempotent** — running the same script twice in a row does not create duplicates (primary keys handle deduplication for transport; replace disposition handles it for weather)
- **Independent** — transport and weather ingestion have no dependency on each other; Airflow runs them in parallel
- **Isolated** — each script writes to its own schema (`transport_raw`, `weather_raw`); there is no cross-contamination between data sources

---

## How to Verify

Run the ingestion scripts manually or trigger the Airflow DAG. Here is what
the terminal output looks like for each script:

**Transport ingestion:**

```
$ docker compose exec dev bash -c 'cd /app && uv run python pipelines/ingestion/transport.py'

Pipeline transport load step completed in 0.03 seconds
1 load package(s) were loaded to destination postgres and into dataset transport_raw
The postgres destination used postgresql://root:***@pgdatabase:5432/rush
Load package 1775723073.833 is LOADED and contains no failed jobs
```

**Weather ingestion:**

```
$ docker compose exec dev bash -c 'cd /app && uv run python pipelines/ingestion/weather.py'

Pipeline weather load step completed in 0.02 seconds
1 load package(s) were loaded to destination postgres and into dataset weather_raw
The postgres destination used postgresql://root:***@pgdatabase:5432/rush
Load package 1775723083.079 is LOADED and contains no failed jobs
```

**Verify data in PostgreSQL:**

```
$ docker compose exec pgdatabase psql -U root -d rush \
    -c "SELECT count(*) FROM transport_raw.departures;"

 count
-------
   100

$ docker compose exec pgdatabase psql -U root -d rush \
    -c "SELECT station, line_name, departure_scheduled, departure_actual
         FROM transport_raw.departures LIMIT 5;"

 station | line_name |    departure_scheduled     |     departure_actual
---------+-----------+----------------------------+---------------------------
 Luzern  | 002466    | 2026-04-09T08:24:00+0200   |
 Luzern  | 021938    | 2026-04-09T08:28:00+0200   | 2026-04-09T08:31:00+0200
 Luzern  | 002117    | 2026-04-09T08:33:00+0200   | 2026-04-09T08:33:00+0200
 Luzern  | 002021    | 2026-04-09T08:34:00+0200   |
 Luzern  | 021438    | 2026-04-09T08:38:00+0200   |
```

A null `departure_actual` means the train is on time (no delay reported by the API).
