"""I/O helpers for the tournament lakehouse."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def ensure_directory(path: Path) -> Path:
    """Create a directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Any:
    """Read any JSON payload from disk."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_json_records(path: Path) -> list[dict[str, Any]]:
    """Read JSON records from disk."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON array in {path}")
    return payload


def write_json(path: Path, payload: Any) -> None:
    """Write any JSON payload to disk."""
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML document from disk."""
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return payload or {}


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    """Write a pandas frame as CSV."""
    ensure_directory(path.parent)
    frame.to_csv(path, index=False)


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV file with pandas."""
    return pd.read_csv(path)
