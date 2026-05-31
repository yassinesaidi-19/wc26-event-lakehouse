"""Streamlit dashboard over processed tournament lakehouse outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from wc2026.paths import QUALITY_DIR, ROOT_DIR
from wc2026.serving import (
    PROCESSED_PATHS,
    ProcessedOutputsNotReadyError,
    build_serving_summary,
    filter_frame,
    list_tournaments,
    load_mart_group_standings,
    load_mart_match_center,
    load_mart_team_performance,
    load_quality_report,
    load_source_contribution_report,
    normalize_int_like_value,
)


PROCESSED_DATA_MESSAGE = "Processed data not found. Run python run_pipeline.py first."
SOURCE_CONTRIBUTION_PATH = QUALITY_DIR / "source_contribution_report.csv"


@st.cache_data(show_spinner=False)
def load_dashboard_data() -> dict[str, object]:
    source_contribution = pd.DataFrame()
    if SOURCE_CONTRIBUTION_PATH.exists():
        source_contribution = load_source_contribution_report()

    return {
        "summary": build_serving_summary(),
        "tournaments": pd.DataFrame(list_tournaments()),
        "group_standings": load_mart_group_standings(),
        "match_center": load_mart_match_center(),
        "team_performance": load_mart_team_performance(),
        "quality_report": load_quality_report(),
        "source_contribution": source_contribution,
    }


def render_metrics(summary: dict[str, int]) -> None:
    labels = [
        ("Tournaments Found", summary["tournaments_found"]),
        ("Teams", summary["teams"]),
        ("Matches", summary["matches"]),
        ("Match Events", summary["match_events"]),
        ("Standings Rows", summary["standings_rows"]),
        ("Quality Passed", summary["quality_checks_passed"]),
        ("Quality Failed", summary["quality_checks_failed"]),
    ]
    columns = st.columns(len(labels))
    for column, (label, value) in zip(columns, labels):
        column.metric(label, value)


def filter_tournament_frame(frame: pd.DataFrame, tournament_id: str, competition_year: int) -> pd.DataFrame:
    return filter_frame(
        frame,
        {
            "tournament_id": tournament_id,
            "competition_year": competition_year,
        },
    )


def render_project_overview(summary: dict[str, int], tournaments: pd.DataFrame) -> None:
    st.header("Project Overview")
    st.write(
        "This project proves an event-driven tournament lakehouse pipeline from raw source ingestion through "
        "canonical models, tournament state, analytics marts, and thin serving layers."
    )
    st.caption(f"Repo root: {ROOT_DIR}")
    render_metrics(summary)
    st.subheader("Architecture Flow")
    st.code(
        "External Sources\n"
        "-> Ingestion Layer\n"
        "-> Immutable Tournament Event Log\n"
        "-> Canonical Tournament Data Model\n"
        "-> Tournament Rules & State Engine\n"
        "-> Analytics Marts\n"
        "-> Serving Layer",
        language="text",
    )
    st.subheader("Required Processed Outputs")
    st.code(
        "\n".join(
            [
                str(PROCESSED_PATHS.mart_group_standings.relative_to(ROOT_DIR)),
                str(PROCESSED_PATHS.mart_match_center.relative_to(ROOT_DIR)),
                str(PROCESSED_PATHS.mart_team_performance.relative_to(ROOT_DIR)),
                str(PROCESSED_PATHS.quality_report.relative_to(ROOT_DIR)),
            ]
        ),
        language="text",
    )
    st.subheader("Tournament Catalog")
    if tournaments.empty:
        st.info("No tournaments are available in the processed outputs yet.")
        return
    st.dataframe(tournaments, use_container_width=True, hide_index=True)


def render_tournament_summary(
    summary: dict[str, int],
    tournaments: pd.DataFrame,
    tournament_id: str | None,
    competition_year: int | None,
    matches: pd.DataFrame,
    standings: pd.DataFrame,
) -> None:
    st.header("Tournament Summary")
    if tournament_id is None or competition_year is None:
        st.info("Tournament summary is not available because no tournament records were loaded.")
        return

    selected = filter_tournament_frame(tournaments, tournament_id, competition_year)
    if not selected.empty:
        st.dataframe(selected, use_container_width=True, hide_index=True)

    tournament_metrics = st.columns(4)
    tournament_metrics[0].metric("Tournament Matches", int(matches["match_id"].nunique()) if not matches.empty else 0)
    tournament_metrics[1].metric("Groups", int(standings["group_id"].nunique()) if not standings.empty else 0)
    tournament_metrics[2].metric("Standing Teams", int(standings["team_id"].nunique()) if not standings.empty else 0)
    tournament_metrics[3].metric("Global Quality Failures", summary["quality_checks_failed"])

    st.subheader("Tournament Matches by Status")
    if matches.empty:
        st.info("No matches available for the selected tournament.")
        return
    status_counts = matches.groupby("status", dropna=False)["match_id"].nunique().reset_index(name="matches")
    st.dataframe(status_counts.sort_values("matches", ascending=False), use_container_width=True, hide_index=True)


def render_group_standings(standings: pd.DataFrame, selected_group: str) -> None:
    st.header("Group Standings")
    filtered = standings if selected_group == "All" else standings[standings["group_id"].astype(str) == str(selected_group)]
    if filtered.empty:
        st.info("No standings rows available for the current selection.")
        return
    display = filtered.sort_values(["group_id", "rank_in_group", "team_name"])
    st.dataframe(display, use_container_width=True, hide_index=True)


def render_match_center(matches: pd.DataFrame, selected_group: str, selected_team: str) -> None:
    st.header("Match Center")
    filtered = matches.copy()
    if selected_group != "All":
        filtered = filtered[filtered["group_id"].astype(str) == str(selected_group)]
    if selected_team != "All":
        filtered = filtered[
            (filtered["home_team_id"].astype(str) == str(selected_team))
            | (filtered["away_team_id"].astype(str) == str(selected_team))
        ]
    if filtered.empty:
        st.info("No matches available for the current selection.")
        return
    st.dataframe(
        filtered.sort_values(["match_date", "match_id"], ascending=[True, True]),
        use_container_width=True,
        hide_index=True,
    )


def render_team_performance(team_performance: pd.DataFrame, selected_team: str) -> None:
    st.header("Team Performance")
    filtered = team_performance if selected_team == "All" else team_performance[team_performance["team_id"].astype(str) == str(selected_team)]
    if filtered.empty:
        st.info("No team performance rows available for the current selection.")
        return
    st.dataframe(
        filtered.sort_values(["points", "goal_difference", "team_name"], ascending=[False, False, True]),
        use_container_width=True,
        hide_index=True,
    )


def render_data_quality(quality_report: dict[str, object]) -> None:
    st.header("Data Quality")
    summary = quality_report.get("summary", {})
    metrics = st.columns(3)
    metrics[0].metric("Status", quality_report.get("status", "unknown"))
    metrics[1].metric("Passed Checks", int(summary.get("passed_checks", 0)))
    metrics[2].metric("Failed Checks", int(summary.get("failed_checks", 0)))
    checks = pd.DataFrame(quality_report.get("checks", []))
    if checks.empty:
        st.info("No data quality checks were recorded.")
        return
    st.dataframe(checks, use_container_width=True, hide_index=True)


def render_source_contribution(source_contribution: pd.DataFrame) -> None:
    st.header("Source Contribution")
    if source_contribution.empty:
        st.info(
            f"Optional file not found: {SOURCE_CONTRIBUTION_PATH.relative_to(ROOT_DIR)}. "
            "Run the pipeline again if you want to regenerate it."
        )
        return
    st.dataframe(source_contribution, use_container_width=True, hide_index=True)


def build_tournament_options(tournaments: pd.DataFrame) -> list[str]:
    if tournaments.empty:
        return []
    return [
        f"{format_competition_year(row['competition_year'])} | {row['tournament_id']}"
        for _, row in tournaments[["competition_year", "tournament_id"]].drop_duplicates().sort_values(
            ["competition_year", "tournament_id"],
            ascending=[False, True],
        ).iterrows()
    ]


def format_competition_year(value: object) -> str:
    normalized = normalize_int_like_value(value)
    return "" if normalized is None else str(normalized)


def parse_selected_tournament(option: str | None) -> tuple[str | None, int | None]:
    if option is None:
        return None, None
    selected_year_text, selected_tournament_id = [part.strip() for part in option.split("|", maxsplit=1)]
    normalized_year = normalize_int_like_value(selected_year_text)
    return selected_tournament_id, int(normalized_year) if normalized_year is not None else None


def safe_selectbox(label: str, options: list[str], default: str = "All") -> str:
    full_options = [default] + options
    return st.sidebar.selectbox(label, full_options, index=0)


def build_optional_values(frame: pd.DataFrame, column_name: str) -> list[str]:
    if column_name not in frame.columns:
        return []
    return sorted(frame[column_name].dropna().astype(str).unique().tolist())


def validate_dashboard_file() -> Path:
    dashboard_path = Path(__file__).resolve()
    if not dashboard_path.exists():
        raise FileNotFoundError(dashboard_path)
    return dashboard_path


def main() -> None:
    validate_dashboard_file()
    st.set_page_config(page_title="World Cup Event Lakehouse", layout="wide")
    st.title("World Cup Event-Driven Tournament Lakehouse")
    st.caption("Local portfolio dashboard over the processed tournament lakehouse outputs.")

    try:
        data = load_dashboard_data()
    except ProcessedOutputsNotReadyError:
        st.error(PROCESSED_DATA_MESSAGE)
        st.stop()

    summary = data["summary"]
    tournaments = data["tournaments"]
    group_standings = data["group_standings"]
    match_center = data["match_center"]
    team_performance = data["team_performance"]
    quality_report = data["quality_report"]
    source_contribution = data["source_contribution"]

    tournament_options = build_tournament_options(tournaments)
    selected_tournament_option = None
    if tournament_options:
        selected_tournament_option = st.sidebar.selectbox("Tournament / Year", tournament_options, index=0)
    else:
        st.sidebar.info("No tournament records were found in the processed outputs.")

    selected_tournament_id, selected_year = parse_selected_tournament(selected_tournament_option)
    tournament_standings = (
        filter_tournament_frame(group_standings, selected_tournament_id, selected_year)
        if selected_tournament_id is not None and selected_year is not None
        else group_standings.copy()
    )
    tournament_matches = (
        filter_tournament_frame(match_center, selected_tournament_id, selected_year)
        if selected_tournament_id is not None and selected_year is not None
        else match_center.copy()
    )
    tournament_team_performance = (
        filter_tournament_frame(team_performance, selected_tournament_id, selected_year)
        if selected_tournament_id is not None and selected_year is not None
        else team_performance.copy()
    )

    selected_group = safe_selectbox("Group", build_optional_values(tournament_standings, "group_id"))
    selected_team = safe_selectbox("Team", build_optional_values(tournament_team_performance, "team_id"))
    section = st.sidebar.radio(
        "Section",
        [
            "Project Overview",
            "Tournament Summary",
            "Group Standings",
            "Match Center",
            "Team Performance",
            "Data Quality",
            "Source Contribution",
        ],
    )

    if section == "Project Overview":
        render_project_overview(summary, tournaments)
    elif section == "Tournament Summary":
        render_tournament_summary(
            summary,
            tournaments,
            selected_tournament_id,
            selected_year,
            tournament_matches,
            tournament_standings,
        )
    elif section == "Group Standings":
        render_group_standings(tournament_standings, selected_group)
    elif section == "Match Center":
        render_match_center(tournament_matches, selected_group, selected_team)
    elif section == "Team Performance":
        render_team_performance(tournament_team_performance, selected_team)
    elif section == "Data Quality":
        render_data_quality(quality_report)
    else:
        render_source_contribution(source_contribution)


if __name__ == "__main__":
    main()
