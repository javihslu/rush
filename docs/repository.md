# 6. Repository Requirements

> **Points: 5** — Source code, Docker configuration, orchestrator setup, README documentation, and professional engineering practices.

---

## Repository Structure

```
rush/
  .github/
    workflows/
      docs.yml              # GitHub Pages deployment (this site)
  dags/
    rush_pipeline.py        # Airflow DAG definitions (2 DAGs)
  docs/                     # Peer review manual (MkDocs source)
  pipelines/
    ingestion/
      transport.py          # SBB/CFF departure ingestion (dlt)
      weather.py            # Open-Meteo weather ingestion (dlt)
    transformation/
      dbt/
        macros/
          delay_minutes.sql # Cross-database delay computation
        models/
          staging/
            sources.yml                      # Source definitions
            stg_transport__departures.sql    # Clean departures
            stg_weather__forecast.sql        # Clean weather
          marts/
            mart_departure_recommendations.sql  # Business table
        dbt_project.yml     # dbt configuration
        profiles.yml        # Database connection profiles
  scripts/
    setup-gcp.sh            # GCP project setup + Terraform
  terraform/
    main.tf                 # GCS bucket + BigQuery dataset
    variables.tf            # Input variables
    outputs.tf              # Resource outputs
  config.yaml               # Central configuration
  config.py                 # Python config loader
  Dockerfile                # Python 3.12 + uv + Airflow
  docker-compose.yaml       # 7-service Docker stack
  pyproject.toml            # Dependencies
  setup.sh                  # One-command setup
  teardown.sh               # Full cleanup
  README.md                 # Quick start and overview
```

---

## Checklist

| Requirement | Status | Location |
|-------------|--------|----------|
| Source code | Present | `pipelines/`, `dags/`, `config.py` |
| Docker configuration | Present | `Dockerfile`, `docker-compose.yaml` |
| Orchestrator setup | Present | `dags/rush_pipeline.py`, Airflow services in docker-compose |
| README documentation | Present | `README.md` with Quick Start, Tech Stack, Project Structure |
| Terraform IaC | Present | `terraform/` with main.tf, variables.tf, outputs.tf |
| `.env` not committed | Correct | `.env` is in `.gitignore`; `.env.example` is provided |
| No hardcoded secrets | Correct | All credentials in `config.yaml` (local dev defaults) |
| Dependencies declared | Present | `pyproject.toml` with pinned dependency groups |

---

## Engineering Practices

**Single source of truth for configuration.** All settings live in `config.yaml`. The setup script generates `.env` for Docker Compose. Python code reads the YAML directly via `config.py`.

**Separation of concerns.** Ingestion, transformation, and orchestration are in separate directories with no circular dependencies. The DAG file imports nothing from the pipeline code — it runs scripts via BashOperator.

**Dual-target dbt models.** All SQL uses ANSI-compatible syntax and dbt macros so the same models run on both PostgreSQL (local) and BigQuery (cloud) without modification. See [Transformation](transformation.md#dual-target-support).

**Reproducible environment.** `setup.sh` handles everything from tool installation to Docker stack startup. A fresh clone on a machine with only Git and Docker can be fully operational in one command.

**Clean teardown.** `teardown.sh` removes all containers, volumes, images, and generated files. It optionally destroys GCP resources via Terraform.

---

## README

The [`README.md`](https://github.com/javihslu/rush/blob/main/README.md) covers:

- Project description and motivation
- One-liner quick start (`bash <(curl ...)`)
- Manual setup for macOS, Linux, and Windows (WSL)
- What the setup script does
- Service URLs after startup
- Tech stack overview
- Data sources with links
- Full project structure tree
- Configuration system
- Development workflow (VS Code Dev Container and terminal-only)
- Teardown instructions
