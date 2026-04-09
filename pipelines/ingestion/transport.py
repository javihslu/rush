"""Ingest Swiss public transport departures from transport.opendata.ch.

Fetches live departure data for configured stations and loads it into
PostgreSQL using dlt in batch mode. Run manually or via Airflow:

    docker compose run --rm dev uv run python pipelines/ingestion/transport.py
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
from config import get_db_url

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = "https://transport.opendata.ch/v1"

# Stations to monitor — covers outbound connections from the office (Luzern)
STATIONS: list[str] = ["Luzern"]

# Limit departures fetched per station per run
DEPARTURES_PER_STATION = 100


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def fetch_stationboard(station: str, limit: int = DEPARTURES_PER_STATION) -> list[dict]:
    """Fetch raw departure records for *station* from the API.

    Args:
        station: Station name as recognised by transport.opendata.ch.
        limit:   Maximum number of departures to return.

    Returns:
        List of raw departure dicts from the API.

    Raises:
        requests.HTTPError: If the API returns a non-2xx status code.
    """
    params = {"station": station, "limit": limit, "transportations[]": ["train"]}
    response = requests.get(f"{API_BASE}/stationboard", params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("stationboard", [])


def parse_departure(raw: dict, station_name: str, ingested_at: str) -> dict:
    """Flatten one raw API departure object into a row for raw storage.

    Performs only structural flattening — no derived fields. All business
    logic (delay calculation, flags) belongs in the dbt staging layer.

    Args:
        raw:          Raw departure dict from the stationboard API.
        station_name: Name of the queried station.
        ingested_at:  ISO-8601 UTC timestamp of the current ingestion batch.

    Returns:
        Flat dict suitable for direct insertion into a database table.
    """
    stop = raw.get("stop", {})
    prognosis = stop.get("prognosis", {}) or {}

    scheduled_departure = stop.get("departure")

    return {
        # Composite natural key: station + line number + scheduled departure
        "id": f"{station_name}__{raw.get('number', '')}_{scheduled_departure}",
        "station": station_name,
        "line_name": raw.get("name"),
        "category": raw.get("category"),
        "line_number": raw.get("number"),
        "operator": raw.get("operator"),
        "destination": raw.get("to"),
        "platform_scheduled": stop.get("platform"),
        "platform_actual": prognosis.get("platform"),
        "departure_scheduled": scheduled_departure,
        "departure_actual": prognosis.get("departure"),
        "ingested_at": ingested_at,
    }


# ---------------------------------------------------------------------------
# dlt source / resource
# ---------------------------------------------------------------------------


@dlt.resource(name="departures", write_disposition="append", primary_key="id")
def departures_resource(stations: list[str] = None) -> Iterator[dict]:
    """Yield one departure record per row for all configured stations.

    Args:
        stations: Station names to query. Defaults to STATIONS if None.

    Yields:
        Flat departure dicts ready for database insertion.
    """
    if stations is None:
        stations = STATIONS
    ingested_at = datetime.now(timezone.utc).isoformat()
    for station in stations:
        raw_list = fetch_stationboard(station)
        for raw in raw_list:
            yield parse_departure(raw, station, ingested_at)


@dlt.source(name="transport")
def transport_source(stations: list[str] = None):
    """dlt source: Swiss public transport departures.

    Args:
        stations: Station names to ingest. Defaults to STATIONS if None.
    """
    return departures_resource(stations)


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def run() -> None:
    """Instantiate and execute the dlt transport pipeline."""
    pipeline = dlt.pipeline(
        pipeline_name="transport",
        destination=dlt.destinations.postgres(credentials=get_db_url()),
        dataset_name="transport_raw",
    )
    load_info = pipeline.run(transport_source())
    print(load_info)


if __name__ == "__main__":
    run()
