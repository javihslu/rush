"""Upload raw data from APIs to Google Cloud Storage.

Fetches transport departures and weather forecasts, then writes them
as newline-delimited JSON files to the project's GCS data lake bucket.

    docker compose exec dev uv run python pipelines/ingestion/cloud_upload.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import storage

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parents[2]))

from pipelines.ingestion.transport import fetch_stationboard, parse_departure, STATIONS
from pipelines.ingestion.weather import fetch_forecast, parse_forecast


def upload_json_to_gcs(bucket_name: str, blob_path: str, records: list[dict]) -> str:
    """Upload a list of dicts as newline-delimited JSON to GCS.

    Args:
        bucket_name: GCS bucket name.
        blob_path:   Object path within the bucket.
        records:     List of dicts to serialize.

    Returns:
        The gs:// URI of the uploaded object.
    """
    client = storage.Client(project=os.environ.get("GCP_PROJECT_ID"))
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    ndjson = "\n".join(json.dumps(r) for r in records)
    blob.upload_from_string(ndjson, content_type="application/json")

    return f"gs://{bucket_name}/{blob_path}"


def upload_transport(bucket_name: str) -> str:
    """Fetch transport data and upload to GCS."""
    ingested_at = datetime.now(timezone.utc).isoformat()
    records = []
    for station in STATIONS:
        raw_list = fetch_stationboard(station)
        for raw in raw_list:
            records.append(parse_departure(raw, station, ingested_at))

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blob_path = f"raw/transport/departures_{date_str}.json"
    uri = upload_json_to_gcs(bucket_name, blob_path, records)
    print(f"Uploaded {len(records)} transport records to {uri}")
    return uri


def upload_weather(bucket_name: str) -> str:
    """Fetch weather data and upload to GCS."""
    ingested_at = datetime.now(timezone.utc).isoformat()
    raw = fetch_forecast()
    records = parse_forecast(raw, ingested_at)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blob_path = f"raw/weather/forecast_{date_str}.json"
    uri = upload_json_to_gcs(bucket_name, blob_path, records)
    print(f"Uploaded {len(records)} weather records to {uri}")
    return uri


def main() -> None:
    """Run both uploads."""
    bucket_name = os.environ.get("GCP_BUCKET_NAME")
    if not bucket_name:
        print("ERROR: GCP_BUCKET_NAME not set. Run setup.sh first.")
        sys.exit(1)

    upload_transport(bucket_name)
    upload_weather(bucket_name)
    print("Cloud ingestion complete.")


if __name__ == "__main__":
    main()
