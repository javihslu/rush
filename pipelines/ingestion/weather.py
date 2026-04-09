"""Ingest weather forecast data from Open-Meteo for the office location.

Fetches a 7-day hourly forecast for Luzern, Switzerland and loads it into
PostgreSQL using dlt. Run manually or via Kestra:

    docker compose run --rm dev uv run python pipelines/ingestion/weather.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import dlt
import requests

# Allow importing config from project root when run as a script
sys.path.insert(0, str(Path(__file__).parents[2]))
from config import cfg

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Office location: Luzern, Switzerland
LATITUDE = 47.0502
LONGITUDE = 8.3093
TIMEZONE = "Europe/Zurich"
FORECAST_DAYS = 7

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Hourly variables relevant to commute decisions
HOURLY_VARIABLES = [
    "temperature_2m",       # °C — affects comfort
    "precipitation",        # mm — rain/snow totals
    "rain",                 # mm — liquid precipitation
    "snowfall",             # cm — snowfall accumulation
    "windspeed_10m",        # km/h — wind at 10 m height
    "weathercode",          # WMO weather interpretation code
    "visibility",           # m — impacts travel conditions
]


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def fetch_forecast() -> dict:
    """Fetch the hourly weather forecast from Open-Meteo.

    Returns:
        Raw API response dict containing parallel hourly arrays.

    Raises:
        requests.HTTPError: If the API returns a non-2xx status code.
    """
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "forecast_days": FORECAST_DAYS,
        "hourly": ",".join(HOURLY_VARIABLES),
    }
    response = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def parse_forecast(raw: dict, ingested_at: str) -> list[dict]:
    """Convert the columnar API response into one dict per forecast hour.

    Open-Meteo returns parallel arrays (one value per hour for each variable).
    This function zips them into individual flat row dicts.

    Args:
        raw:         Raw API response from Open-Meteo.
        ingested_at: ISO-8601 UTC timestamp of the ingestion batch.

    Returns:
        List of flat dicts, one per forecast hour (up to 7 * 24 = 168 rows).
    """
    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    records = []

    for i, time_str in enumerate(times):
        record: dict = {
            "id": f"{LATITUDE}_{LONGITUDE}_{time_str}",
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "forecast_time": time_str,
            "ingested_at": ingested_at,
        }
        for var in HOURLY_VARIABLES:
            values = hourly.get(var, [])
            record[var] = values[i] if i < len(values) else None

        records.append(record)

    return records


# ---------------------------------------------------------------------------
# dlt source / resource
# ---------------------------------------------------------------------------


@dlt.resource(name="hourly_forecast", write_disposition="replace", primary_key="id")
def forecast_resource() -> Iterator[dict]:
    """Yield one weather record per forecast hour for Luzern.

    Uses write_disposition='replace' so each pipeline run refreshes the
    full 7-day forecast window rather than accumulating duplicates.

    Yields:
        Flat weather dicts ready for database insertion.
    """
    ingested_at = datetime.now(timezone.utc).isoformat()
    for record in parse_forecast(fetch_forecast(), ingested_at):
        yield record


@dlt.source(name="weather")
def weather_source():
    """dlt source: Open-Meteo hourly forecast for Luzern, Switzerland."""
    return forecast_resource()


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def build_connection_string() -> str:
    """Build a PostgreSQL DSN from config.yaml values."""
    db = cfg["database"]
    return f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"


def run() -> None:
    """Instantiate and execute the dlt weather pipeline."""
    pipeline = dlt.pipeline(
        pipeline_name="weather",
        destination=dlt.destinations.postgres(credentials=build_connection_string()),
        dataset_name="weather_raw",
    )
    load_info = pipeline.run(weather_source())
    print(load_info)


if __name__ == "__main__":
    run()
