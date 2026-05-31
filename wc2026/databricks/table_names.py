"""Databricks table naming and local-output mapping helpers."""

from __future__ import annotations

from pathlib import Path

from wc2026.paths import CANONICAL_DIR, EVENT_LOG_DIR, MARTS_DIR, QUALITY_DIR, STATE_DIR


LOCAL_OUTPUT_SPECS: dict[str, dict[str, object]] = {
    "event_log": {"path": EVENT_LOG_DIR / "event_log.csv", "schema_key": "event_log", "format": "csv"},
    "dim_team": {"path": CANONICAL_DIR / "dim_team.csv", "schema_key": "canonical", "format": "csv"},
    "dim_player": {"path": CANONICAL_DIR / "dim_player.csv", "schema_key": "canonical", "format": "csv"},
    "fact_match": {"path": CANONICAL_DIR / "fact_match.csv", "schema_key": "canonical", "format": "csv"},
    "fact_match_event": {"path": CANONICAL_DIR / "fact_match_event.csv", "schema_key": "canonical", "format": "csv"},
    "state_group_standings": {"path": STATE_DIR / "state_group_standings.csv", "schema_key": "state", "format": "csv"},
    "state_qualification_status": {"path": STATE_DIR / "state_qualification_status.csv", "schema_key": "state", "format": "csv"},
    "mart_group_standings": {"path": MARTS_DIR / "mart_group_standings.csv", "schema_key": "marts", "format": "csv"},
    "mart_match_center": {"path": MARTS_DIR / "mart_match_center.csv", "schema_key": "marts", "format": "csv"},
    "mart_team_performance": {"path": MARTS_DIR / "mart_team_performance.csv", "schema_key": "marts", "format": "csv"},
    "source_contribution_report": {
        "path": QUALITY_DIR / "source_contribution_report.csv",
        "schema_key": "quality",
        "format": "csv",
    },
    "quality_report": {"path": QUALITY_DIR / "quality_report.json", "schema_key": "quality", "format": "json"},
}


def build_table_targets(config: dict[str, object]) -> dict[str, dict[str, object]]:
    """Build fully qualified table names and local-path mappings."""
    catalog = str(config["catalog"])
    schemas = dict(config["schemas"])
    tables = dict(config["tables"])
    targets: dict[str, dict[str, object]] = {}
    for table_key, spec in LOCAL_OUTPUT_SPECS.items():
        schema_name = str(schemas[str(spec["schema_key"])])
        table_name = str(tables[table_key])
        targets[table_key] = {
            "catalog": catalog,
            "schema": schema_name,
            "table": table_name,
            "full_name": f"{catalog}.{schema_name}.{table_name}",
            "path": Path(spec["path"]),
            "format": spec["format"],
        }
    return targets
