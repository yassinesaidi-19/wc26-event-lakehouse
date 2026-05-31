"""Shared readers for the local API and dashboard serving layers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from wc2026.io_utils import read_csv, read_json
from wc2026.paths import CANONICAL_DIR, EVENT_LOG_DIR, MARTS_DIR, QUALITY_DIR, STATE_DIR


class ProcessedOutputsNotReadyError(FileNotFoundError):
    """Raised when the processed pipeline outputs are not available."""


@dataclass(frozen=True)
class ProcessedPathSet:
    event_log: Path = EVENT_LOG_DIR / "event_log.csv"
    dim_team: Path = CANONICAL_DIR / "dim_team.csv"
    fact_match: Path = CANONICAL_DIR / "fact_match.csv"
    fact_match_event: Path = CANONICAL_DIR / "fact_match_event.csv"
    state_group_standings: Path = STATE_DIR / "state_group_standings.csv"
    mart_group_standings: Path = MARTS_DIR / "mart_group_standings.csv"
    mart_match_center: Path = MARTS_DIR / "mart_match_center.csv"
    mart_team_performance: Path = MARTS_DIR / "mart_team_performance.csv"
    quality_report: Path = QUALITY_DIR / "quality_report.json"
    source_contribution_report: Path = QUALITY_DIR / "source_contribution_report.csv"


PROCESSED_PATHS = ProcessedPathSet()


def normalize_int_like_value(value: Any) -> Any:
    """Convert values like 2006.0 or '2006.0' into integer 2006 for stable comparisons."""
    if value is None or pd.isna(value):
        return None

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            numeric = float(stripped)
        except ValueError:
            return stripped
        if numeric.is_integer():
            return int(numeric)
        return stripped

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def _require_path(path: Path) -> Path:
    if not path.exists():
        raise ProcessedOutputsNotReadyError(f"Missing processed output: {path}")
    return path


def load_event_log() -> pd.DataFrame:
    return read_csv(_require_path(PROCESSED_PATHS.event_log))


def load_dim_team() -> pd.DataFrame:
    return read_csv(_require_path(PROCESSED_PATHS.dim_team))


def load_fact_match() -> pd.DataFrame:
    return read_csv(_require_path(PROCESSED_PATHS.fact_match))


def load_fact_match_event() -> pd.DataFrame:
    return read_csv(_require_path(PROCESSED_PATHS.fact_match_event))


def load_state_group_standings() -> pd.DataFrame:
    return read_csv(_require_path(PROCESSED_PATHS.state_group_standings))


def load_mart_group_standings() -> pd.DataFrame:
    return read_csv(_require_path(PROCESSED_PATHS.mart_group_standings))


def load_mart_match_center() -> pd.DataFrame:
    return read_csv(_require_path(PROCESSED_PATHS.mart_match_center))


def load_mart_team_performance() -> pd.DataFrame:
    return read_csv(_require_path(PROCESSED_PATHS.mart_team_performance))


def load_quality_report() -> dict[str, Any]:
    return read_json(_require_path(PROCESSED_PATHS.quality_report))


def load_source_contribution_report() -> pd.DataFrame:
    return read_csv(_require_path(PROCESSED_PATHS.source_contribution_report))


def build_serving_summary() -> dict[str, int]:
    event_log = load_event_log()
    dim_team = load_dim_team()
    fact_match = load_fact_match()
    fact_match_event = load_fact_match_event()
    standings = load_state_group_standings()
    quality_report = load_quality_report()
    report_summary = quality_report.get("summary", {})
    return {
        "events_created": int(len(event_log)),
        "teams": int(len(dim_team)),
        "matches": int(len(fact_match)),
        "match_events": int(len(fact_match_event)),
        "standings_rows": int(len(standings)),
        "tournaments_found": int(standings["tournament_id"].nunique()) if not standings.empty else 0,
        "groups_generated": int(standings[["tournament_id", "group_id"]].drop_duplicates().shape[0]) if not standings.empty else 0,
        "quality_checks_passed": int(report_summary.get("passed_checks", 0)),
        "quality_checks_failed": int(report_summary.get("failed_checks", 0)),
    }


def list_tournaments() -> list[dict[str, Any]]:
    matches = load_fact_match()
    if matches.empty:
        return []

    group_counts = (
        matches[matches["group_id"].notna()]
        .groupby(["tournament_id", "competition_year"], dropna=False)["group_id"]
        .nunique()
        .reset_index(name="groups_present")
    )
    grouped = (
        matches.groupby(
            ["tournament_id", "competition_name", "competition_year", "source_name"],
            dropna=False,
        )
        .agg(
            match_count=("match_id", "nunique"),
            finished_match_count=("status", lambda values: int(values.astype(str).str.upper().isin({"FINISHED", "FT", "AET", "PEN", "COMPLETED"}).sum())),
            first_match_date=("match_date", "min"),
            last_match_date=("match_date", "max"),
        )
        .reset_index()
    )
    grouped = grouped.merge(group_counts, on=["tournament_id", "competition_year"], how="left")
    grouped["groups_present"] = grouped["groups_present"].fillna(0).astype(int)
    grouped = grouped.sort_values(["competition_year", "tournament_id"], ascending=[False, True])
    grouped["competition_year"] = grouped["competition_year"].map(normalize_int_like_value)
    return grouped.to_dict(orient="records")


def filter_frame(frame: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    filtered = frame.copy()
    for column, value in filters.items():
        if value is None or column not in filtered.columns:
            continue
        normalized_value = normalize_int_like_value(value)
        normalized_column = filtered[column].map(normalize_int_like_value)
        filtered = filtered[normalized_column == normalized_value]
    return filtered
