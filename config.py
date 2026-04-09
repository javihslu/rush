"""Central configuration loader.

Reads config.yaml and exposes values to all Python code.

Usage:
    from config import cfg

    print(cfg["database"]["host"])
    print(cfg["project"]["name"])
"""

from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent / "config.yaml"

with _CONFIG_PATH.open() as f:
    cfg = yaml.safe_load(f)


def get_db_url() -> str:
    """Build a PostgreSQL DSN from config.yaml values."""
    db = cfg["database"]
    return f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"