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

```bash
git clone git@github.com:javihslu/rush.git
cd rush
./setup.sh
```

The setup script checks for required tools and offers to install anything missing
(Homebrew on macOS, apt/dnf on Linux). It handles the full setup:

1. Installs missing prerequisites (gcloud CLI, Terraform) if you agree
2. Creates `.env` from template
3. Starts the local Docker stack (PostgreSQL, pgAdmin)
4. Authenticates with Google Cloud (two browser logins)
5. Creates a GCP project, links billing, enables APIs
6. Generates `gcp_config.json` and `terraform.tfvars`
7. Runs `terraform apply` to provision GCS bucket and BigQuery dataset

The only things you need beforehand:
- [Git](https://git-scm.com/downloads)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)

Everything else (`gcloud`, `terraform`) is installed for you if missing.

Once running:
- pgAdmin: http://localhost:8085 (configurable via `PGADMIN_PORT_HOST` in `.env`)
- PostgreSQL: `localhost:5432` (configurable via `POSTGRES_PORT_HOST` in `.env`)

To stop: `docker compose down`

## Tech Stack

- **Ingestion**: dlt, Python
- **Orchestration**: Kestra
- **Warehouse**: DuckDB / BigQuery
- **Transformation**: dbt
- **Infrastructure**: Docker, Terraform

## Data Sources

- [opentransportdata.swiss](https://opentransportdata.swiss) -- SBB/CFF schedules and delay data
- [Open-Meteo](https://open-meteo.com) -- Weather forecasts and historical data (Swiss-based, free)

## Project Structure

```
rush/
  ingestion/            # data ingestion scripts
    transport.py        # SBB/CFF schedules and delays
    weather.py          # Open-Meteo weather data
  transformation/       # data transformation logic
    transform.py        # merge transport + weather, compute features
  orchestration/        # Kestra flow definitions
  terraform/            # GCP infrastructure as code
  notebooks/            # exploratory analysis
  .devcontainer/        # VS Code Dev Container config
  Dockerfile            # dev container (Python 3.13 + uv + deps)
  docker-compose.yaml   # full dev stack
  setup.sh              # one-command setup (local stack + GCP onboarding)
  pyproject.toml        # Python dependencies (uv)
  .env.example          # environment variable template
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
docker compose run --rm dev uv run python ingestion/transport.py

# open a shell inside the container
docker compose run --rm dev bash

# run jupyter
docker compose run --rm -p 8888:8888 dev uv run jupyter notebook --ip=0.0.0.0 --no-browser --allow-root
```

Source code is mounted from your host, so edits in any editor are reflected immediately.

## Status

Project setup
