"""Configuration helpers for the Databricks execution path."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from wc2026.io_utils import read_yaml
from wc2026.paths import CONFIGS_DIR


REQUIRED_SCHEMA_KEYS = {"event_log", "canonical", "state", "marts", "quality"}
REQUIRED_TABLE_KEYS = {
    "event_log",
    "dim_team",
    "dim_player",
    "fact_match",
    "fact_match_event",
    "state_group_standings",
    "state_qualification_status",
    "mart_group_standings",
    "mart_match_center",
    "mart_team_performance",
    "source_contribution_report",
    "quality_report",
}


def load_databricks_config(path: Path | None = None) -> dict[str, Any]:
    """Load and validate Databricks configuration."""
    config_path = path or (CONFIGS_DIR / "databricks.yml")
    payload = deepcopy(read_yaml(config_path))
    if not payload:
        raise ValueError(f"Databricks config is empty: {config_path}")
    if "catalog" not in payload or not str(payload["catalog"]).strip():
        raise ValueError("Databricks config must define a non-empty catalog")

    schemas = payload.get("schemas", {})
    tables = payload.get("tables", {})
    missing_schemas = sorted(REQUIRED_SCHEMA_KEYS - set(schemas))
    missing_tables = sorted(REQUIRED_TABLE_KEYS - set(tables))
    if missing_schemas:
        raise ValueError(f"Databricks config is missing schemas: {', '.join(missing_schemas)}")
    if missing_tables:
        raise ValueError(f"Databricks config is missing tables: {', '.join(missing_tables)}")
    return payload
