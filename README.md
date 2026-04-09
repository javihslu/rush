# Rush

**Your office escape advisor.** Rush tells you the perfect moment to flee the building —
before the sky opens up, the trains break down, and everyone else has the same idea.

> Full documentation and peer review manual: [javihslu.github.io/rush](https://javihslu.github.io/rush/)

## Overview

Rush combines Swiss public transport schedules and weather forecasts to answer the only
question that matters at 5 PM: *"Should I leave now, or wait it out?"*

**What it watches:**
- Live SBB/CFF departures and delays from your office station
- 7-day hourly weather forecast — temperature, rain, snow, wind, visibility

**What it tells you:** A departure recommendation (Ideal / Good / Risky / Bad) based
on current delays and weather conditions.

## Quick Start

One command sets up everything on macOS, Linux, or Windows (WSL):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/javihslu/rush/main/install.sh)
```

This clones the repository, checks for required tools (installing anything
missing), and starts the full Docker stack. If you already have the repo
cloned, run `./setup.sh` from inside it.

<details>
<summary><strong>Windows</strong></summary>

1. Open PowerShell as Administrator and install WSL 2:
   ```powershell
   wsl --install
   ```
2. Restart your computer
3. Install [Docker Desktop](https://www.docker.com/products/docker-desktop) (enable WSL 2 backend in settings)
4. Open your WSL terminal (Ubuntu) and run the command above

</details>

What the setup does:

1. Checks for Git, Docker, gcloud CLI, and Terraform -- offers to install anything missing
2. Reads `config.yaml` and generates a `.env` file for Docker Compose
3. Builds and starts all Docker containers (`docker compose up -d --build`)
4. If gcloud is available, runs `scripts/setup-gcp.sh` for cloud onboarding
5. Prints service URLs when everything is ready

Once running:
- Airflow: http://localhost:8080 (workflow orchestration UI)
- pgAdmin: http://localhost:8085
- PostgreSQL: `localhost:5432`

If you have port conflicts, stop the other containers before running `setup.sh`.

To stop: `docker compose down`

To fully clean up (containers, volumes, images, generated files):
```bash
./teardown.sh
```

## Tech Stack

- **Ingestion**: dlt, Python (local); google-cloud-storage, google-cloud-bigquery (cloud)
- **Orchestration**: Apache Airflow (4 DAGs -- 2 local, 2 cloud)
- **Warehouse**: PostgreSQL (local) / BigQuery (cloud)
- **Data Lake**: Google Cloud Storage
- **Transformation**: dbt (dual-target: PostgreSQL + BigQuery)
- **Infrastructure**: Docker, Terraform

## Data Sources

- [transport.opendata.ch](https://transport.opendata.ch) -- SBB/CFF schedules and delay data
- [Open-Meteo](https://open-meteo.com) -- Weather forecasts and historical data (Swiss-based, free)

## Project Structure

```
rush/
  pipelines/                # all data pipeline code
    ingestion/              # data ingestion scripts
      transport.py          # SBB/CFF departures and delays (dlt -> PostgreSQL)
      weather.py            # Open-Meteo weather forecasts (dlt -> PostgreSQL)
      cloud_upload.py       # Upload raw data to GCS data lake
      cloud_load_bq.py      # Load GCS data into BigQuery raw datasets
    transformation/         # data transformation
      dbt/                  # dbt project
        dbt_project.yml
        models/
          staging/          # raw -> cleaned views
          marts/            # business-ready tables
      transform.py          # ad-hoc Python transforms
  dags/                     # Airflow DAG definitions
    rush_pipeline.py        # Local DAGs (ingestion + transformation)
    rush_cloud_pipeline.py  # Cloud DAGs (GCS + BigQuery + dbt prod)
  terraform/                # GCP infrastructure (Terraform)
    main.tf                 # GCS bucket + BigQuery dataset
    variables.tf            # input variables
    outputs.tf              # resource outputs
  scripts/                  # helper scripts
    setup-gcp.sh            # GCP project creation + auth + Terraform
  notebooks/                # exploratory analysis
  .devcontainer/            # VS Code Dev Container config
  config.yaml               # central configuration (single source of truth)
  config.py                 # Python config loader
  Dockerfile                # dev container (Python 3.12 + uv + Airflow)
  docker-compose.yaml       # full dev stack
  setup.sh                  # one-command setup (local stack + GCP)
  teardown.sh               # full cleanup (containers, volumes, images, GCP)
  pyproject.toml            # Python dependencies (uv)
```

## Configuration

All configuration lives in `config.yaml` — the single source of truth.
`setup.sh` generates `.env` from it for Docker Compose. Python code reads it directly.

```yaml
project:
  name: rush

database:
  user: root
  password: root
  name: rush
  host: pgdatabase
  port: 5432

pgadmin:
  email: admin@admin.com
  password: root

airflow:
  user: airflow
  password: airflow

gcp:
  region: europe-west6
```

To apply changes: edit `config.yaml`, delete `.env`, and re-run `./setup.sh`.

In Python:
```python
from config import cfg

db_host = cfg["database"]["host"]
```

## Development

All development runs inside Docker. No local Python installation required.

### VS Code + Dev Containers (recommended)

1. Install [VS Code](https://code.visualstudio.com/) (free)
2. Install the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension
3. Open the `rush` folder in VS Code
4. Click "Reopen in Container" when prompted (or run `Dev Containers: Reopen in Container` from the command palette)

VS Code will build the container, start PostgreSQL and pgAdmin, install all dependencies, and open a terminal inside the dev environment. Python autocomplete, debugging, and Jupyter all work out of the box.

### Terminal only (no VS Code)

If you prefer your own editor, just use Docker directly:

```bash
# run a script
docker compose run --rm dev uv run python pipelines/ingestion/transport.py

# open a shell inside the container
docker compose run --rm dev bash

# run jupyter
docker compose run --rm -p 8888:8888 dev uv run jupyter notebook --ip=0.0.0.0 --no-browser --allow-root
```

Source code is mounted from your host, so edits in any editor are reflected immediately.
