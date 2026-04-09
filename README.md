# Rush

**Your office escape advisor.** Rush tells you the perfect moment to flee the building —
before the sky opens up, the trains break down, and everyone else has the same idea.

## Overview

Rush crunches Swiss public transport schedules, weather forecasts, and historical traffic
patterns to answer the only question that matters at 5 PM: *"Should I run for it now, or am
I already doomed?"*

**What it watches:**
- Your escape route (office location → home station)
- Live SBB/CFF departures, delays, and cancellations
- Current and forecasted weather — because nobody wants to sprint through hail
- Time of day, day of week, and seasonal chaos patterns

**What it tells you:** The optimal escape window — minimizing wait time, weather misery,
and the odds of being sardined into an overcrowded train.

## Quick Start

One-liner (requires Git and Docker):
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/javihslu/rush/main/install.sh)
```

Or set up manually:

### Prerequisites

<details>
<summary><strong>macOS / Linux</strong></summary>

1. Install [Git](https://git-scm.com/downloads)
2. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
3. Clone and run:
   ```bash
   git clone git@github.com:javihslu/rush.git
   cd rush
   ./setup.sh
   ```

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Open PowerShell as Administrator and install WSL 2:
   ```powershell
   wsl --install
   ```
2. Restart your computer
3. Install [Docker Desktop](https://www.docker.com/products/docker-desktop) (enable WSL 2 backend in settings)
4. Open your WSL terminal (Ubuntu) and run:
   ```bash
   bash <(curl -fsSL https://raw.githubusercontent.com/javihslu/rush/main/install.sh)
   ```

</details>

The setup script checks for required tools and offers to install anything missing
(Homebrew on macOS, apt/dnf on Linux). It handles the full setup:

1. Installs missing prerequisites (gcloud CLI, Terraform) if you agree
2. Creates `.env` from `config.yaml`
3. Starts the local Docker stack (PostgreSQL, pgAdmin, Airflow)
4. Runs `scripts/setup-gcp.sh` for cloud onboarding (auth, project, billing, APIs, Terraform)

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

- **Ingestion**: dlt, Python
- **Orchestration**: Apache Airflow
- **Warehouse**: PostgreSQL / BigQuery
- **Transformation**: dbt
- **Infrastructure**: Docker, Terraform

## Data Sources

- [transport.opendata.ch](https://transport.opendata.ch) -- SBB/CFF schedules and delay data
- [Open-Meteo](https://open-meteo.com) -- Weather forecasts and historical data (Swiss-based, free)

## Project Structure

```
rush/
  pipelines/                # all data pipeline code
    ingestion/              # data ingestion scripts (dlt)
      transport.py          # SBB/CFF departures and delays
      weather.py            # Open-Meteo weather forecasts
    transformation/         # data transformation
      dbt/                  # dbt project
        dbt_project.yml
        models/
          staging/          # raw -> cleaned views
          marts/            # business-ready tables
      transform.py          # ad-hoc Python transforms
  dags/                     # Airflow DAG definitions
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
