FROM python:3.12-slim

# system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

# install Airflow (separate from uv — Airflow has strict dependency constraints)
ARG AIRFLOW_VERSION=2.10.5
ARG PYTHON_VERSION=3.12
RUN pip install --no-cache-dir "apache-airflow[postgres]==${AIRFLOW_VERSION}" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

WORKDIR /app

# install dependencies first (cached layer)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# copy project source
COPY . .

# install with dev dependencies
RUN uv sync

# validate critical imports work at build time
RUN uv run python -c "import pandas; import numpy; import pytz; print(f'OK: pandas={pandas.__version__} numpy={numpy.__version__} pytz={pytz.__version__}')"

CMD ["uv", "run", "python"]
