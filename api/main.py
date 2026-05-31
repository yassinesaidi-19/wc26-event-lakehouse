"""FastAPI serving layer over processed tournament outputs."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from wc2026.serving import (
    ProcessedOutputsNotReadyError,
    build_serving_summary,
    filter_frame,
    list_tournaments,
    load_dim_team,
    load_fact_match,
    load_mart_match_center,
    load_mart_team_performance,
    load_quality_report,
    load_state_group_standings,
)


app = FastAPI(
    title="World Cup 2026 Event Lakehouse API",
    description="Local serving layer over the processed tournament lakehouse outputs.",
    version="1.0.0",
)


def _missing_outputs_detail(exc: ProcessedOutputsNotReadyError) -> str:
    return f"{exc}. Run python run_pipeline.py first."


@app.exception_handler(ProcessedOutputsNotReadyError)
def processed_outputs_not_ready_handler(
    _request: Request,
    exc: ProcessedOutputsNotReadyError,
) -> JSONResponse:
    """Return a clean serving error when processed files are not ready yet."""
    return JSONResponse(
        status_code=503,
        content={"detail": _missing_outputs_detail(exc)},
    )


@app.get("/")
def root() -> dict[str, Any]:
    """Describe the API surface."""
    return {
        "service": "world-cup-2026-event-lakehouse",
        "status_endpoint": "/health",
        "summary_endpoint": "/summary",
        "available_endpoints": [
            "/",
            "/health",
            "/summary",
            "/tournaments",
            "/standings",
            "/standings/{tournament_id}",
            "/matches",
            "/matches/{match_id}",
            "/teams",
            "/teams/{team_id}",
            "/quality",
        ],
    }


@app.get("/health")
def health() -> dict[str, Any]:
    """Return a lightweight readiness response."""
    try:
        summary = build_serving_summary()
    except ProcessedOutputsNotReadyError:
        return {"status": "degraded", "outputs_ready": False}
    return {"status": "ok", "outputs_ready": True, "summary": summary}


@app.get("/summary")
def summary() -> dict[str, int]:
    """Return serving-layer summary counts."""
    return build_serving_summary()


@app.get("/tournaments")
def tournaments() -> list[dict[str, Any]]:
    """Return tournament catalog entries from canonical matches."""
    return list_tournaments()


@app.get("/standings")
def standings(
    tournament_id: str | None = None,
    competition_year: int | None = None,
    group_id: str | None = None,
    team_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return filtered standings rows."""
    frame = load_state_group_standings()
    filtered = filter_frame(
        frame,
        {
            "tournament_id": tournament_id,
            "competition_year": competition_year,
            "group_id": group_id,
            "team_id": team_id,
        },
    )
    filtered = filtered.sort_values(
        ["competition_year", "tournament_id", "group_id", "rank_in_group"],
        ascending=[False, True, True, True],
    )
    return filtered.to_dict(orient="records")


@app.get("/standings/{tournament_id}")
def standings_by_tournament(tournament_id: str) -> list[dict[str, Any]]:
    """Return standings rows for a single tournament."""
    return standings(tournament_id=tournament_id)


@app.get("/matches")
def matches(
    tournament_id: str | None = None,
    competition_year: int | None = None,
    group_id: str | None = None,
    team_id: str | None = None,
    status: str | None = None,
    source_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return filtered match-center rows."""
    frame = load_mart_match_center()

    filtered = filter_frame(
        frame,
        {
            "tournament_id": tournament_id,
            "competition_year": competition_year,
            "group_id": group_id,
            "status": status,
            "source_name": source_name,
        },
    )
    if team_id is not None:
        filtered = filtered[
            (filtered["home_team_id"].astype(str) == str(team_id))
            | (filtered["away_team_id"].astype(str) == str(team_id))
        ]
    filtered = filtered.sort_values(["competition_year", "match_date", "match_id"], ascending=[False, True, True])
    return filtered.to_dict(orient="records")


@app.get("/matches/{match_id}")
def match_detail(match_id: str) -> dict[str, Any]:
    """Return one match-center row."""
    rows = matches()
    for row in rows:
        if str(row.get("match_id")) == str(match_id):
            return row
    raise HTTPException(status_code=404, detail=f"Match not found: {match_id}")


@app.get("/teams")
def teams(
    tournament_id: str | None = None,
    competition_year: int | None = None,
    team_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return tournament-aware team performance rows joined with team metadata."""
    performance = load_mart_team_performance()
    dim_team = load_dim_team()

    filtered = filter_frame(
        performance,
        {
            "tournament_id": tournament_id,
            "competition_year": competition_year,
            "team_id": team_id,
        },
    )
    team_meta = dim_team[["team_id", "team_name", "confederation", "country_code", "source_name"]].drop_duplicates(
        ["team_id"]
    )
    merged = filtered.merge(team_meta, on=["team_id", "team_name"], how="left", suffixes=("", "_dim"))
    merged = merged.sort_values(["competition_year", "points", "goal_difference", "team_name"], ascending=[False, False, False, True])
    return merged.to_dict(orient="records")


@app.get("/teams/{team_id}")
def team_detail(team_id: str) -> dict[str, Any]:
    """Return team metadata plus tournament performance rows."""
    dim_team = load_dim_team()
    performance = load_mart_team_performance()
    matches_frame = load_fact_match()

    team_rows = dim_team[dim_team["team_id"].astype(str) == str(team_id)]
    if team_rows.empty:
        raise HTTPException(status_code=404, detail=f"Team not found: {team_id}")

    performance_rows = performance[performance["team_id"].astype(str) == str(team_id)].sort_values(
        ["competition_year", "points", "goal_difference"],
        ascending=[False, False, False],
    )
    team_matches = matches_frame[
        (matches_frame["home_team_id"].astype(str) == str(team_id))
        | (matches_frame["away_team_id"].astype(str) == str(team_id))
    ]
    return {
        "team": team_rows.iloc[0].to_dict(),
        "performances": performance_rows.to_dict(orient="records"),
        "match_count": int(team_matches["match_id"].nunique()),
    }


@app.get("/quality")
def quality() -> dict[str, Any]:
    """Return the persisted quality report."""
    return load_quality_report()
