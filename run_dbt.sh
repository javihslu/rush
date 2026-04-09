#!/bin/bash
sudo docker compose run --rm dev bash -c "uv run dbt run --project-dir pipelines/transformation/dbt --profiles-dir pipelines/transformation/dbt"
