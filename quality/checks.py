"""Reusable quality checks for tournament lakehouse outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

FINISHED_STATUSES = {"FINISHED", "FT", "AET", "PEN", "COMPLETED"}


def ensure_required_columns(frame: pd.DataFrame, required_columns: list[str], dataset_name: str) -> list[str]:
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        return [f"{dataset_name} is missing required columns: {', '.join(missing)}"]
    return []


def build_quality_report(
    event_log_path: Path,
    dim_team_path: Path,
    fact_match_path: Path,
    fact_match_event_path: Path,
    standings_path: Path,
    source_contribution_path: Path,
    ingestion_runs_path: Path,
    allowed_event_types: set[str],
) -> dict[str, object]:
    """Run the requested quality checks and return a structured report."""
    event_log = pd.read_csv(event_log_path)
    dim_team = pd.read_csv(dim_team_path)
    fact_match = pd.read_csv(fact_match_path)
    fact_match_event = pd.read_csv(fact_match_event_path)
    standings = pd.read_csv(standings_path)
    source_contribution = pd.read_csv(source_contribution_path)
    ingestion_runs = pd.read_json(ingestion_runs_path)

    checks: list[dict[str, object]] = []

    def record_check(name: str, fn: Callable[[], tuple[bool, str]]) -> None:
        passed, detail = fn()
        checks.append({"check_name": name, "passed": passed, "detail": detail})

    record_check(
        "required_columns_event_log",
        lambda: _errors_to_result(
            ensure_required_columns(
                event_log,
                [
                    "event_id",
                    "source_name",
                    "event_type",
                    "entity_type",
                    "entity_id",
                    "match_id",
                    "team_id",
                    "player_id",
                    "payload_json",
                    "source_timestamp",
                    "ingestion_timestamp",
                    "batch_id",
                    "schema_version",
                    "is_valid",
                    "error_reason",
                ],
                "event_log",
            )
        ),
    )
    record_check(
        "required_columns_dim_team",
        lambda: _errors_to_result(
            ensure_required_columns(
                dim_team,
                ["team_id", "team_name", "country_code", "confederation", "group_id", "is_host", "source_name", "source_entity_id"],
                "dim_team",
            )
        ),
    )
    record_check(
        "required_columns_fact_match",
        lambda: _errors_to_result(
            ensure_required_columns(
                fact_match,
                [
                    "match_id",
                    "tournament_id",
                    "competition_name",
                    "competition_year",
                    "home_team_id",
                    "away_team_id",
                    "home_team_name",
                    "away_team_name",
                    "stadium",
                    "host_city",
                    "stage",
                    "group_id",
                    "match_date",
                    "status",
                    "home_score",
                    "away_score",
                    "winner_team_id",
                    "source_name",
                    "source_entity_id",
                ],
                "fact_match",
            )
        ),
    )
    record_check(
        "required_columns_fact_match_event",
        lambda: _errors_to_result(
            ensure_required_columns(
                fact_match_event,
                [
                    "event_id",
                    "match_id",
                    "event_minute",
                    "event_type",
                    "team_id",
                    "player_id",
                    "player_name",
                    "related_player_id",
                    "related_player_name",
                    "event_detail",
                    "source_name",
                    "source_entity_id",
                ],
                "fact_match_event",
            )
        ),
    )
    record_check(
        "required_columns_source_contribution_report",
        lambda: _errors_to_result(
            ensure_required_columns(
                source_contribution,
                [
                    "source_name",
                    "teams_count",
                    "matches_count",
                    "match_events_count",
                    "finished_matches_count",
                    "scheduled_matches_count",
                    "live_matches_count",
                    "event_log_count",
                ],
                "source_contribution_report",
            )
        ),
    )
    record_check(
        "required_columns_state_group_standings",
        lambda: _errors_to_result(
            ensure_required_columns(
                standings,
                [
                    "tournament_id",
                    "competition_year",
                    "group_id",
                    "team_id",
                    "team_name",
                    "matches_played",
                    "wins",
                    "draws",
                    "losses",
                    "goals_for",
                    "goals_against",
                    "goal_difference",
                    "points",
                    "rank_in_group",
                ],
                "state_group_standings",
            )
        ),
    )
    record_check(
        "event_id_unique",
        lambda: (
            not event_log["event_id"].duplicated().any(),
            "event_log.event_id values are unique"
            if not event_log["event_id"].duplicated().any()
            else "event_log.event_id must be unique",
        ),
    )
    record_check(
        "event_type_valid",
        lambda: _invalid_event_types_result(event_log, allowed_event_types),
    )
    record_check(
        "match_id_present_for_match_events",
        lambda: (
            not fact_match_event[
                fact_match_event["event_type"].isin(
                    {"MATCH_STARTED", "GOAL_SCORED", "YELLOW_CARD", "RED_CARD", "SUBSTITUTION", "MATCH_FINISHED"}
                )
            ]["match_id"].isna().any(),
            "fact_match_event.match_id populated for match events"
            if not fact_match_event[
                fact_match_event["event_type"].isin(
                    {"MATCH_STARTED", "GOAL_SCORED", "YELLOW_CARD", "RED_CARD", "SUBSTITUTION", "MATCH_FINISHED"}
                )
            ]["match_id"].isna().any()
            else "fact_match_event.match_id must not be null for match events",
        ),
    )
    record_check(
        "team_id_exists_when_needed",
        lambda: _team_membership_result(dim_team, fact_match_event),
    )
    record_check(
        "match_has_two_different_teams",
        lambda: _distinct_teams_result(fact_match),
    )
    record_check(
        "scores_non_negative",
        lambda: _non_negative_scores_result(fact_match),
    )
    record_check(
        "points_formula_correct",
        lambda: _points_formula_result(standings),
    )
    record_check(
        "goal_difference_correct",
        lambda: _goal_difference_result(standings),
    )
    record_check(
        "finished_group_match_contributes_two_team_rows",
        lambda: _finished_group_match_row_result(fact_match, standings),
    )
    record_check(
        "group_not_mixed_across_tournament_years",
        lambda: _group_year_consistency_result(standings),
    )
    record_check(
        "api_matches_have_source_name",
        lambda: _api_source_name_result(fact_match),
    )
    record_check(
        "api_matches_have_source_entity_id",
        lambda: _api_source_entity_result(fact_match),
    )
    record_check(
        "api_matches_have_canonical_status",
        lambda: _api_status_result(fact_match),
    )
    record_check(
        "api_finished_matches_have_non_negative_scores",
        lambda: _api_score_result(fact_match),
    )
    record_check(
        "api_team_ids_are_source_prefixed",
        lambda: _api_team_prefix_result(dim_team),
    )
    record_check(
        "api_match_ids_are_source_prefixed",
        lambda: _api_match_prefix_result(fact_match),
    )
    record_check(
        "api_normalization_did_not_fail_pipeline",
        lambda: _api_normalization_run_result(ingestion_runs),
    )

    passed_checks = sum(1 for check in checks if check["passed"])
    failed_checks = len(checks) - passed_checks

    return {
        "status": "passed" if failed_checks == 0 else "failed",
        "checks": checks,
        "summary": {
            "total_checks": len(checks),
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
        },
        "row_counts": {
            "event_log": int(len(event_log)),
            "dim_team": int(len(dim_team)),
            "fact_match": int(len(fact_match)),
            "fact_match_event": int(len(fact_match_event)),
            "state_group_standings": int(len(standings)),
            "source_contribution_report": int(len(source_contribution)),
        },
    }


def validate_pipeline_outputs(
    event_log_path: Path,
    dim_team_path: Path,
    fact_match_path: Path,
    fact_match_event_path: Path,
    standings_path: Path,
    source_contribution_path: Path,
    ingestion_runs_path: Path,
    allowed_event_types: set[str],
) -> dict[str, object]:
    """Run the requested quality checks and raise on failure."""
    report = build_quality_report(
        event_log_path=event_log_path,
        dim_team_path=dim_team_path,
        fact_match_path=fact_match_path,
        fact_match_event_path=fact_match_event_path,
        standings_path=standings_path,
        source_contribution_path=source_contribution_path,
        ingestion_runs_path=ingestion_runs_path,
        allowed_event_types=allowed_event_types,
    )
    failed_details = [check["detail"] for check in report["checks"] if not check["passed"]]
    if failed_details:
        raise ValueError("\n".join(str(detail) for detail in failed_details))
    return report


def _errors_to_result(errors: list[str]) -> tuple[bool, str]:
    return (not errors, "passed" if not errors else "; ".join(errors))


def _invalid_event_types_result(event_log: pd.DataFrame, allowed_event_types: set[str]) -> tuple[bool, str]:
    invalid_event_types = sorted(set(event_log.loc[~event_log["event_type"].isin(allowed_event_types), "event_type"]))
    if invalid_event_types:
        return False, f"Invalid event types found: {', '.join(invalid_event_types)}"
    return True, "All event types are valid"


def _team_membership_result(dim_team: pd.DataFrame, fact_match_event: pd.DataFrame) -> tuple[bool, str]:
    team_ids = set(dim_team["team_id"].dropna().astype(str))
    event_team_ids = set(fact_match_event["team_id"].dropna().astype(str))
    missing_teams = sorted(event_team_ids - team_ids)
    if missing_teams:
        return False, f"fact_match_event.team_id must exist in dim_team: {', '.join(missing_teams[:10])}"
    return True, "All event team IDs exist in dim_team"


def _distinct_teams_result(fact_match: pd.DataFrame) -> tuple[bool, str]:
    same_team_matches = fact_match[
        fact_match["home_team_id"].notna()
        & fact_match["away_team_id"].notna()
        & (fact_match["home_team_id"].astype(str) == fact_match["away_team_id"].astype(str))
    ]
    if not same_team_matches.empty:
        return False, "fact_match contains matches where home_team_id equals away_team_id"
    return True, "All matches have two different teams when both teams are known"


def _non_negative_scores_result(fact_match: pd.DataFrame) -> tuple[bool, str]:
    score_frame = fact_match[fact_match["home_score"].notna() & fact_match["away_score"].notna()]
    if ((score_frame["home_score"] < 0) | (score_frame["away_score"] < 0)).any():
        return False, "fact_match scores must be non-negative"
    return True, "All populated scores are non-negative"


def _points_formula_result(standings: pd.DataFrame) -> tuple[bool, str]:
    standings_points = standings["wins"] * 3 + standings["draws"]
    if not standings_points.equals(standings["points"]):
        return False, "state_group_standings points must equal wins * 3 + draws"
    return True, "Points match wins * 3 + draws"


def _goal_difference_result(standings: pd.DataFrame) -> tuple[bool, str]:
    goal_difference = standings["goals_for"] - standings["goals_against"]
    if not goal_difference.equals(standings["goal_difference"]):
        return False, "state_group_standings goal_difference must equal goals_for - goals_against"
    return True, "Goal difference matches goals_for - goals_against"


def _finished_group_match_row_result(fact_match: pd.DataFrame, standings: pd.DataFrame) -> tuple[bool, str]:
    finished_group_matches = fact_match[
        fact_match["group_id"].notna()
        & fact_match["tournament_id"].notna()
        & fact_match["competition_year"].notna()
        & fact_match["home_team_id"].notna()
        & fact_match["away_team_id"].notna()
        & fact_match["home_score"].notna()
        & fact_match["away_score"].notna()
        & fact_match["status"].astype(str).str.upper().isin(FINISHED_STATUSES)
    ]
    finished_group_matches = finished_group_matches[
        ~finished_group_matches["group_id"].astype(str).str.strip().str.lower().isin({"not applicable", "n/a", "none", "nan", "null", ""})
    ]
    for _, match in finished_group_matches.iterrows():
        tournament_rows = standings[
            (standings["tournament_id"] == match["tournament_id"])
            & (standings["competition_year"] == match["competition_year"])
            & (standings["group_id"] == match["group_id"])
            & (standings["team_id"].isin([match["home_team_id"], match["away_team_id"]]))
        ]
        if tournament_rows["team_id"].nunique() != 2:
            return False, "Every finished group-stage match must contribute exactly two standings team rows"
    return True, "Every finished group-stage match contributes two standings team rows"


def _group_year_consistency_result(standings: pd.DataFrame) -> tuple[bool, str]:
    grouped = (
        standings.groupby(["tournament_id", "group_id"], dropna=False)["competition_year"]
        .nunique(dropna=True)
        .reset_index(name="year_count")
    )
    if (grouped["year_count"] > 1).any():
        return False, "No group may mix teams from different tournament years"
    return True, "No group mixes teams from different tournament years"


def _api_rows(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["source_name"].astype(str).isin({"api_football", "football_data"})].copy()


def _api_source_name_result(fact_match: pd.DataFrame) -> tuple[bool, str]:
    api_matches = _api_rows(fact_match)
    if api_matches["source_name"].isna().any():
        return False, "API normalized matches must have source_name"
    return True, "API normalized matches have source_name"


def _api_source_entity_result(fact_match: pd.DataFrame) -> tuple[bool, str]:
    api_matches = _api_rows(fact_match)
    if api_matches["source_entity_id"].isna().any() or (api_matches["source_entity_id"].astype(str).str.strip() == "").any():
        return False, "API normalized matches must have source_entity_id"
    return True, "API normalized matches have source_entity_id"


def _api_status_result(fact_match: pd.DataFrame) -> tuple[bool, str]:
    api_matches = _api_rows(fact_match)
    allowed = {"SCHEDULED", "LIVE", "FINISHED", "POSTPONED", "CANCELLED", "UNKNOWN"}
    invalid = sorted(set(api_matches.loc[~api_matches["status"].astype(str).isin(allowed), "status"].astype(str)))
    if invalid:
        return False, f"API normalized matches must have canonical statuses only: {', '.join(invalid)}"
    return True, "API normalized matches have canonical statuses"


def _api_score_result(fact_match: pd.DataFrame) -> tuple[bool, str]:
    api_matches = _api_rows(fact_match)
    finished = api_matches[api_matches["status"].astype(str) == "FINISHED"]
    with_scores = finished[finished["home_score"].notna() & finished["away_score"].notna()]
    if ((with_scores["home_score"] < 0) | (with_scores["away_score"] < 0)).any():
        return False, "Finished API matches must not have negative scores"
    return True, "Finished API matches have non-negative scores when scores exist"


def _api_team_prefix_result(dim_team: pd.DataFrame) -> tuple[bool, str]:
    api_teams = _api_rows(dim_team)
    valid = api_teams.apply(
        lambda row: str(row["team_id"]).startswith("API_FOOTBALL_TEAM_")
        if row["source_name"] == "api_football"
        else str(row["team_id"]).startswith("FOOTBALL_DATA_TEAM_"),
        axis=1,
    )
    if not valid.all():
        return False, "API team IDs must be source-prefixed"
    return True, "API team IDs are source-prefixed"


def _api_match_prefix_result(fact_match: pd.DataFrame) -> tuple[bool, str]:
    api_matches = _api_rows(fact_match)
    valid = api_matches.apply(
        lambda row: str(row["match_id"]).startswith("API_FOOTBALL_MATCH_")
        if row["source_name"] == "api_football"
        else str(row["match_id"]).startswith("FOOTBALL_DATA_MATCH_"),
        axis=1,
    )
    if not valid.all():
        return False, "API match IDs must be source-prefixed"
    return True, "API match IDs are source-prefixed"


def _api_normalization_run_result(ingestion_runs: pd.DataFrame) -> tuple[bool, str]:
    required = {"api_football_normalization", "football_data_normalization"}
    available = set(ingestion_runs.get("source_name", pd.Series(dtype=str)).dropna().astype(str))
    if not required.issubset(available):
        return False, "API normalization runs must be recorded in ingestion metadata"
    relevant = ingestion_runs[ingestion_runs["source_name"].astype(str).isin(required)]
    if (relevant["status"].astype(str) == "failed").any():
        return False, "API payload parsing must not stop the pipeline"
    return True, "API payload parsing did not stop the pipeline"
