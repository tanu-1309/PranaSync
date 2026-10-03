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


def database_url() -> str:
    """SQLite by default so the demo runs anywhere; set DATABASE_URL for PostgreSQL,
    e.g. postgresql+psycopg2://prana:secret@localhost:5432/prana"""
    return os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'prana.db'}")
