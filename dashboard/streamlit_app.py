"""Streamlit dashboard over processed tournament lakehouse outputs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from wc2026.serving import (
    ProcessedOutputsNotReadyError,
    build_serving_summary,
    list_tournaments,
    load_mart_group_standings,
    load_mart_match_center,
    load_mart_team_performance,
    load_quality_report,
)


st.set_page_config(page_title="World Cup Event Lakehouse", layout="wide")


@st.cache_data(show_spinner=False)
def load_dashboard_data() -> dict[str, object]:
    return {
        "summary": build_serving_summary(),
        "tournaments": pd.DataFrame(list_tournaments()),
        "group_standings": load_mart_group_standings(),
        "match_center": load_mart_match_center(),
        "team_performance": load_mart_team_performance(),
        "quality_report": load_quality_report(),
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
    filtered = frame.copy()
    if "tournament_id" in filtered.columns:
        filtered = filtered[filtered["tournament_id"].astype(str) == str(tournament_id)]
    if "competition_year" in filtered.columns:
        filtered = filtered[filtered["competition_year"].astype(str) == str(competition_year)]
    return filtered


def render_project_overview(summary: dict[str, int], tournaments: pd.DataFrame) -> None:
    st.header("Project Overview")
    st.write(
        "This project proves an event-driven tournament lakehouse pipeline from raw source ingestion through "
        "canonical models, tournament state, analytics marts, and thin serving layers."
    )
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
    st.subheader("Tournament Catalog")
    st.dataframe(tournaments, use_container_width=True, hide_index=True)


def render_tournament_summary(
    summary: dict[str, int],
    tournaments: pd.DataFrame,
    tournament_id: str,
    competition_year: int,
    matches: pd.DataFrame,
    standings: pd.DataFrame,
) -> None:
    st.header("Tournament Summary")
    selected = tournaments[
        (tournaments["tournament_id"].astype(str) == str(tournament_id))
        & (tournaments["competition_year"].astype(str) == str(competition_year))
    ]
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
    else:
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


def render_quality_report(quality_report: dict[str, object]) -> None:
    st.header("Data Quality Report")
    summary = quality_report.get("summary", {})
    metrics = st.columns(3)
    metrics[0].metric("Status", quality_report.get("status", "unknown"))
    metrics[1].metric("Passed Checks", int(summary.get("passed_checks", 0)))
    metrics[2].metric("Failed Checks", int(summary.get("failed_checks", 0)))
    checks = pd.DataFrame(quality_report.get("checks", []))
    st.dataframe(checks, use_container_width=True, hide_index=True)


def render_architecture_explanation() -> None:
    st.header("Architecture Explanation")
    st.markdown(
        """
        **External Sources** feed the project from four modes: local sample JSON, downloaded public datasets,
        API-Football, and football-data.org.

        **Ingestion Layer** records source availability, captures raw API payloads, and preserves secret hygiene by
        keeping API keys in `.env` instead of `data/raw/`.

        **Immutable Event Log** converts usable records into a replayable event stream at
        `data/processed/event_log/event_log.csv`.

        **Canonical Model** resolves the event stream into `dim_team`, `dim_player`, `fact_match`, and
        `fact_match_event`.

        **Tournament Rules & State Engine** computes standings from canonical `fact_match.csv`, separated by
        `tournament_id` and `competition_year` so historical tournaments never mix with the 2026 sample run.

        **Analytics Marts** publish serving-friendly tables for standings, match center views, and team performance.

        **Serving Layer** exposes the marts and quality report through this dashboard and the FastAPI app.
        """
    )


st.title("World Cup Event-Driven Tournament Lakehouse")
st.caption("Local portfolio dashboard over the processed tournament lakehouse outputs.")

try:
    data = load_dashboard_data()
except ProcessedOutputsNotReadyError:
    st.error("Processed outputs are missing. Run `python run_pipeline.py` from the repo root first.")
    st.stop()

summary = data["summary"]
tournaments = data["tournaments"]
group_standings = data["group_standings"]
match_center = data["match_center"]
team_performance = data["team_performance"]
quality_report = data["quality_report"]

tournament_options = [
    f"{row['competition_year']} | {row['tournament_id']}"
    for _, row in tournaments[["competition_year", "tournament_id"]].drop_duplicates().sort_values(
        ["competition_year", "tournament_id"],
        ascending=[False, True],
    ).iterrows()
]

selected_tournament_option = st.sidebar.selectbox("Tournament / Year", tournament_options, index=0)
selected_year_text, selected_tournament_id = [part.strip() for part in selected_tournament_option.split("|", maxsplit=1)]
selected_year = int(selected_year_text)

tournament_standings = filter_tournament_frame(group_standings, selected_tournament_id, selected_year)
tournament_matches = filter_tournament_frame(match_center, selected_tournament_id, selected_year)
tournament_team_performance = filter_tournament_frame(team_performance, selected_tournament_id, selected_year)

group_options = ["All"] + sorted(tournament_standings["group_id"].dropna().astype(str).unique().tolist())
team_options = ["All"] + sorted(tournament_team_performance["team_id"].dropna().astype(str).unique().tolist())

selected_group = st.sidebar.selectbox("Group", group_options, index=0)
selected_team = st.sidebar.selectbox("Team", team_options, index=0)
section = st.sidebar.radio(
    "Section",
    [
        "Project Overview",
        "Tournament Summary",
        "Group Standings",
        "Match Center",
        "Team Performance",
        "Data Quality Report",
        "Architecture Explanation",
    ],
)

if section == "Project Overview":
    render_project_overview(summary, tournaments)
elif section == "Tournament Summary":
    render_tournament_summary(summary, tournaments, selected_tournament_id, selected_year, tournament_matches, tournament_standings)
elif section == "Group Standings":
    render_group_standings(tournament_standings, selected_group)
elif section == "Match Center":
    render_match_center(tournament_matches, selected_group, selected_team)
elif section == "Team Performance":
    render_team_performance(tournament_team_performance, selected_team)
elif section == "Data Quality Report":
    render_quality_report(quality_report)
else:
    render_architecture_explanation()
