"""Central configuration loader.

Reads config.yaml and exposes values to all Python code.

Usage:
    from config import cfg

    print(cfg["database"]["host"])
    print(cfg["project"]["name"])


from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent / "config.yaml"

with _CONFIG_PATH.open() as f:
    cfg = yaml.safe_load(f)
"""

from pathlib import Path
import yaml

_CONFIG_PATH = Path(__file__).parent / "config.yaml"
_ENV_PATH = Path(__file__).parent / ".env"


def flatten(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            items.extend(flatten(v, new_key, sep=sep).items())

        elif isinstance(v, list):
            # Liste zu comma-separated string
            items.append((new_key.upper(), ",".join(map(str, v))))

        else:
            items.append((new_key.upper(), v))

    return dict(items)


with _CONFIG_PATH.open() as f:
    cfg = yaml.safe_load(f)

flat_cfg = flatten(cfg)

with _ENV_PATH.open("w") as f:
    for key, value in flat_cfg.items():
        f.write(f"{key}={value}\n")

print("✅ .env wurde neu generiert")