FROM python:3.13-slim

# system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# install Airflow (separate from uv — Airflow has strict dependency constraints)
ARG AIRFLOW_VERSION=2.10.5
ARG PYTHON_VERSION=3.13
RUN pip install --no-cache-dir "apache-airflow[postgres]==${AIRFLOW_VERSION}" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

WORKDIR /app

# install dependencies first (cached layer)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync

# copy project source
COPY . .

# install with dev dependencies
RUN uv sync

CMD ["uv", "run", "python"]
