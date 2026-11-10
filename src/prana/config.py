"""Shared configuration helpers (paths, YAML config, environment)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RAW_DIR = Path(os.getenv("PRANA_RAW_DIR", DATA_DIR / "raw"))
SYNTHETIC_DIR = DATA_DIR / "synthetic"
RESULTS_DIR = ROOT / "results"


@lru_cache(maxsize=None)
def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def column_map() -> dict:
    return load_yaml("column_map.yaml")


def scenarios_config() -> dict:
    return load_yaml("scenarios.yaml")


@lru_cache(maxsize=None)
def _dotenv() -> dict:
    """KEY=VALUE lines from the git-ignored .env file in the project root (real environment variables win)."""
    path = ROOT / ".env"
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def setting(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or _dotenv().get(name) or default


def database_url() -> str:
    """PostgreSQL when DATABASE_URL is set (environment or .env), SQLite otherwise so the demo and CI need no server.
    e.g. postgresql+psycopg2://pranasync:secret@127.0.0.1:5433/pranasync  (scripts/pg_local.py creates one for development)"""
    return setting("DATABASE_URL") or f"sqlite:///{DATA_DIR / 'prana.db'}"
