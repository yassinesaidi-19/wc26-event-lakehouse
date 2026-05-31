"""Core orchestration functions for the tournament lakehouse MVP."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.normalizers import normalize_api_football_payloads, normalize_football_data_payloads
from quality.checks import validate_pipeline_outputs
from transformations.event_log.event_factory import EventFactory
from wc2026.io_utils import ensure_directory, read_csv, read_yaml, write_csv, write_json
from wc2026.models import IngestionRunRecord
from wc2026.paths import (
    CANONICAL_DIR,
    CONFIGS_DIR,
    EVENT_LOG_DIR,
    MARTS_DIR,
    QUALITY_DIR,
    RAW_API_FOOTBALL_DIR,
    RAW_FOOTBALL_DATA_DIR,
    RAW_INGESTION_METADATA_DIR,
    SAMPLE_DIR,
    STATE_DIR,
)
from wc2026.project_setup import api_key_exists, load_local_env, organize_data_folders
from wc2026.source_loaders import (
    explore_dataset_files,
    load_api_football_payload,
    load_fjelstul_matches,
    load_fjelstul_players,
    load_fjelstul_teams,
    load_football_data_payload,
    load_openfootball_matches,
    load_openfootball_teams,
    load_sample_fixtures,
    load_sample_match_events,
    load_sample_teams,
)
from wc2026.status import normalize_match_status


EVENT_TYPES = {
    "TEAM_REGISTERED",
    "PLAYER_REGISTERED",
    "MATCH_SCHEDULED",
    "MATCH_STARTED",
    "GOAL_SCORED",
    "YELLOW_CARD",
    "RED_CARD",
    "SUBSTITUTION",
    "MATCH_FINISHED",
    "STANDING_UPDATED",
    "TEAM_QUALIFIED",
    "TEAM_ELIMINATED",
    "BRACKET_UPDATED",
}

MATCH_EVENT_TYPES = {
    "MATCH_STARTED",
    "GOAL_SCORED",
    "YELLOW_CARD",
    "RED_CARD",
    "SUBSTITUTION",
    "MATCH_FINISHED",
}

SOURCE_PRIORITY = {
    "sample": 0,
    "api_football": 1,
    "football_data": 2,
    "openfootball": 3,
    "fjelstul": 4,
}

CURRENT_TOURNAMENT_SOURCES = {"sample", "openfootball", "api_football", "football_data"}
FINISHED_STATUSES = {"FINISHED", "FT", "AET", "PEN", "COMPLETED"}
SAMPLE_TOURNAMENT_ID = "SAMPLE-WC-2026"
OPENFOOTBALL_TOURNAMENT_ID = "OPENFOOTBALL-WC-2026"
CANONICAL_STATUSES = {"SCHEDULED", "LIVE", "FINISHED", "POSTPONED", "CANCELLED", "UNKNOWN"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _batch_id() -> str:
    return f"batch-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _rules() -> dict[str, Any]:
    return read_yaml(CONFIGS_DIR / "tournament_rules.yml")


def _extract_year(value: object) -> int | None:
    if value is None:
        return None
    text = str(value)
    match = re.search(r"(19|20)\d{2}", text)
    if match:
        return int(match.group(0))
    return None


def _winner_from_scores(
    home_score: object,
    away_score: object,
    home_team_id: object,
    away_team_id: object,
) -> str | None:
    if home_score is None or away_score is None:
        return None
    try:
        home_value = int(home_score)
        away_value = int(away_score)
    except (TypeError, ValueError):
        return None
    if home_value > away_value:
        return _normalize_team_ref(home_team_id)
    if away_value > home_value:
        return _normalize_team_ref(away_team_id)
    return None


def _is_finished_status(value: object) -> bool:
    if value is None:
        return False
    return str(value).strip().upper() in FINISHED_STATUSES


def _is_meaningful_group_id(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    return text not in {"", "none", "nan", "not applicable", "n/a", "null"}


def _group_match_candidates(fact_match: pd.DataFrame) -> pd.DataFrame:
    candidates = fact_match[
        fact_match["group_id"].notna()
        & fact_match["tournament_id"].notna()
        & fact_match["competition_year"].notna()
        & fact_match["home_team_id"].notna()
        & fact_match["away_team_id"].notna()
    ].copy()
    return candidates[candidates["group_id"].apply(_is_meaningful_group_id)].copy()


def _finished_group_matches(fact_match: pd.DataFrame) -> pd.DataFrame:
    candidates = _group_match_candidates(fact_match)
    finished_mask = candidates["status"].apply(_is_finished_status)
    score_mask = candidates["home_score"].notna() & candidates["away_score"].notna()
    return candidates[finished_mask & score_mask].copy()


def _ingestion_runs_path() -> Path:
    ensure_directory(RAW_INGESTION_METADATA_DIR)
    return RAW_INGESTION_METADATA_DIR / "ingestion_runs.json"


def _append_ingestion_run(record: IngestionRunRecord) -> None:
    path = _ingestion_runs_path()
    payload: list[dict[str, Any]] = []
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = []
    payload.append(record.model_dump())
    write_json(path, payload)


def _write_run(source_name: str, status: str, record_count: int, output_path: Path | None, detail: str | None = None) -> None:
    now = _utc_now()
    _append_ingestion_run(
        IngestionRunRecord(
            run_id=f"{source_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            source_name=source_name,
            status=status,
            record_count=record_count,
            output_path=str(output_path) if output_path else None,
            detail=detail,
            started_at=now,
            completed_at=now,
        )
    )


def initialize_ingestion_run_log() -> None:
    """Start a fresh ingestion metadata log for the current pipeline run."""
    write_json(_ingestion_runs_path(), [])


def ingest_local_sample_files() -> dict[str, int]:
    """Validate sample source availability and record ingestion metadata."""
    teams = load_sample_teams()
    fixtures = load_sample_fixtures()
    match_events = load_sample_match_events()
    _write_run("sample_teams", "completed", len(teams), SAMPLE_DIR / "teams.json")
    _write_run("sample_fixtures", "completed", len(fixtures), SAMPLE_DIR / "fixtures.json")
    _write_run("sample_match_events", "completed", len(match_events), SAMPLE_DIR / "match_events.json")
    return {"teams": len(teams), "fixtures": len(fixtures), "match_events": len(match_events)}


def ingest_openfootball() -> dict[str, Any]:
    """Explore and validate the openfootball dataset."""
    files = explore_dataset_files((CONFIGS_DIR.parent / "data" / "external" / "openfootball" / "worldcup.json-master"))
    teams = load_openfootball_teams()
    matches = load_openfootball_matches()
    _write_run("openfootball", "completed", len(teams) + len(matches), None, detail=f"{len(files)} files discovered")
    return {"files": files, "teams": len(teams), "matches": len(matches)}


def ingest_fjelstul() -> dict[str, Any]:
    """Explore and validate the Fjelstul World Cup database."""
    files = explore_dataset_files((CONFIGS_DIR.parent / "data" / "external" / "fjelstul" / "worldcup-master"))
    teams = load_fjelstul_teams()
    players = load_fjelstul_players()
    matches = load_fjelstul_matches()
    _write_run("fjelstul", "completed", len(teams) + len(players) + len(matches), None, detail=f"{len(files)} files discovered")
    return {"files": files, "teams": len(teams), "players": len(players), "matches": len(matches)}


def ingest_api_sources(include_api: bool = True) -> list[str]:
    """Run API ingestion when requested and local keys are available."""
    messages: list[str] = []
    if not include_api:
        messages.append("API ingestion disabled for this run.")
        return messages

    load_local_env()

    if api_key_exists("API_FOOTBALL_KEY"):
        try:
            from ingestion.api_clients.api_football_client import APIFootballClient

            client = APIFootballClient()
            output_paths = client.fetch_all()
            _write_run("api_football", "completed", len(output_paths), RAW_API_FOOTBALL_DIR, detail="fixtures, teams, standings")
            messages.append("API-Football raw payloads fetched.")
        except Exception as exc:
            _write_run("api_football", "failed", 0, None, detail=str(exc))
            messages.append("API-Football ingestion failed; continuing with local and public data.")
    else:
        _write_run("api_football", "skipped", 0, None, detail="Missing API_FOOTBALL_KEY")
        messages.append("API-Football key missing; skipping API ingestion.")

    if api_key_exists("FOOTBALL_DATA_KEY"):
        try:
            from ingestion.api_clients.football_data_client import FootballDataClient

            client = FootballDataClient()
            output_paths = client.fetch_all()
            _write_run("football_data", "completed", len(output_paths), RAW_FOOTBALL_DATA_DIR, detail="matches, teams, standings")
            messages.append("football-data.org raw payloads fetched.")
        except Exception as exc:
            _write_run("football_data", "failed", 0, None, detail=str(exc))
            messages.append("football-data.org ingestion failed; continuing with local and public data.")
    else:
        _write_run("football_data", "skipped", 0, None, detail="Missing FOOTBALL_DATA_KEY")
        messages.append("football-data.org key missing; skipping API ingestion.")

    return messages


def build_event_log() -> Path:
    """Normalize available sources into the immutable tournament event log."""
    factory = EventFactory(batch_id=_batch_id(), ingestion_timestamp=_utc_now())
    events: list[dict[str, Any]] = []

    for record in load_sample_teams():
        events.append(
            factory.create_team_registered(
                source_name="sample",
                entity_id=record["team_id"],
                team_id=record["team_id"],
                payload={
                    **record,
                    "source_name": "sample",
                },
                source_timestamp=record.get("source_timestamp"),
            )
        )

    for record in load_sample_fixtures():
        events.append(
            factory.create_match_scheduled(
                source_name="sample",
                entity_id=record["match_id"],
                match_id=record["match_id"],
                payload={
                    **record,
                    "tournament_id": SAMPLE_TOURNAMENT_ID,
                    "competition_name": "FIFA World Cup 2026 Sample",
                    "competition_year": 2026,
                    "source_name": "sample",
                },
                source_timestamp=record.get("source_timestamp"),
            )
        )

    for record in load_sample_match_events():
        events.append(
            factory.create_match_event(
                source_name="sample",
                entity_id=record["source_event_id"],
                event_type=record["event_type"],
                match_id=record["match_id"],
                team_id=record.get("team_id"),
                player_id=record.get("player_id"),
                payload={
                    **record,
                    "source_name": "sample",
                },
                source_timestamp=record.get("source_timestamp"),
            )
        )

    for record in load_openfootball_teams():
        team_id = record.get("fifa_code") or record.get("name")
        events.append(
            factory.create_team_registered(
                source_name="openfootball",
                entity_id=str(team_id),
                team_id=str(team_id),
                payload={
                    "team_id": str(team_id),
                    "team_name": record.get("name"),
                    "country_code": record.get("fifa_code"),
                    "confederation": record.get("confed"),
                    "group_id": str(record.get("group", "")).replace("Group ", ""),
                    "is_host": str(record.get("name")) in {"Mexico", "Canada", "United States"},
                    "source_name": "openfootball",
                },
                source_timestamp=None,
            )
        )

    for index, record in enumerate(load_openfootball_matches(), start=1):
        match_id = f"OF-2026-{index:03d}"
        group_name = str(record.get("group", "")).replace("Group ", "")
        events.append(
            factory.create_match_scheduled(
                source_name="openfootball",
                entity_id=match_id,
                match_id=match_id,
                payload={
                    "match_id": match_id,
                    "home_team_id": record.get("team1"),
                    "away_team_id": record.get("team2"),
                    "stadium": record.get("ground"),
                    "host_city": record.get("ground"),
                    "stage": record.get("round"),
                    "group_id": group_name or None,
                    "match_date": record.get("date"),
                    "status": "SCHEDULED",
                    "tournament_id": OPENFOOTBALL_TOURNAMENT_ID,
                    "competition_name": "World Cup 2026",
                    "competition_year": 2026,
                    "source_name": "openfootball",
                },
                source_timestamp=record.get("date"),
            )
        )

    for record in load_fjelstul_teams():
        events.append(
            factory.create_team_registered(
                source_name="fjelstul",
                entity_id=record["team_id"],
                team_id=record["team_id"],
                payload={
                    "team_id": record["team_id"],
                    "team_name": record.get("team_name"),
                    "country_code": record.get("team_code"),
                    "confederation": record.get("confederation_code"),
                    "group_id": None,
                    "is_host": False,
                    "source_name": "fjelstul",
                },
                source_timestamp=None,
            )
        )

    for record in load_fjelstul_players():
        position = None
        if record.get("goal_keeper") == 1:
            position = "Goalkeeper"
        elif record.get("defender") == 1:
            position = "Defender"
        elif record.get("midfielder") == 1:
            position = "Midfielder"
        elif record.get("forward") == 1:
            position = "Forward"
        events.append(
            factory.create_player_registered(
                source_name="fjelstul",
                entity_id=record["player_id"],
                player_id=record["player_id"],
                payload={
                    "player_id": record["player_id"],
                    "player_name": " ".join(
                        part for part in [record.get("given_name"), record.get("family_name")] if part
                    ).strip(),
                    "team_id": None,
                    "position": position,
                    "shirt_number": None,
                    "birth_date": record.get("birth_date"),
                    "club": None,
                    "source_name": "fjelstul",
                },
                source_timestamp=record.get("birth_date"),
            )
        )

    for record in load_fjelstul_matches():
        match_id = record["match_id"]
        stage = record.get("stage_name")
        group_name = record.get("group_name")
        competition_year = _extract_year(record.get("tournament_name")) or _extract_year(record.get("tournament_id"))
        home_team_id = record.get("home_team_code") or record.get("home_team_id")
        away_team_id = record.get("away_team_code") or record.get("away_team_id")
        events.append(
            factory.create_match_scheduled(
                source_name="fjelstul",
                entity_id=match_id,
                match_id=match_id,
                payload={
                    "match_id": match_id,
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "stadium": record.get("stadium_name"),
                    "host_city": record.get("city_name"),
                    "stage": stage,
                    "group_id": group_name,
                    "match_date": record.get("match_date"),
                    "status": "FINISHED",
                    "home_score": int(record.get("home_team_score", 0)),
                    "away_score": int(record.get("away_team_score", 0)),
                    "winner_team_id": _winner_from_scores(
                        record.get("home_team_score"),
                        record.get("away_team_score"),
                        home_team_id,
                        away_team_id,
                    ),
                    "tournament_id": record.get("tournament_id"),
                    "competition_name": record.get("tournament_name"),
                    "competition_year": competition_year,
                    "source_name": "fjelstul",
                },
                source_timestamp=record.get("match_date"),
            )
        )
        events.append(
            factory.create_match_event(
                source_name="fjelstul",
                entity_id=f"{match_id}-finished",
                event_type="MATCH_FINISHED",
                match_id=match_id,
                team_id=None,
                player_id=None,
                payload={
                    "match_id": match_id,
                    "event_minute": 90,
                    "event_detail": record.get("score"),
                    "home_score": int(record.get("home_team_score", 0)),
                    "away_score": int(record.get("away_team_score", 0)),
                    "winner_team_id": _winner_from_scores(
                        record.get("home_team_score"),
                        record.get("away_team_score"),
                        home_team_id,
                        away_team_id,
                    ),
                    "source_name": "fjelstul",
                },
                source_timestamp=record.get("match_date"),
            )
        )

    _extend_events_from_api_payloads(factory, events)

    event_frame = pd.DataFrame(events)
    event_frame = event_frame.sort_values(["source_name", "event_type", "entity_id"]).reset_index(drop=True)
    output_path = EVENT_LOG_DIR / "event_log.csv"
    write_csv(output_path, event_frame)
    return output_path


def _standard_team_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "team_id": record.get("team_id"),
        "team_name": record.get("team_name"),
        "country_code": record.get("country_code"),
        "confederation": record.get("confederation"),
        "group_id": record.get("group_id"),
        "is_host": bool(record.get("is_host", False)),
        "source_name": record.get("source_name"),
        "source_entity_id": record.get("source_entity_id"),
        "raw_source_file": record.get("raw_source_file"),
    }


def _standard_match_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "match_id": record.get("match_id"),
        "tournament_id": record.get("tournament_id"),
        "competition_name": record.get("competition_name"),
        "competition_year": record.get("competition_year"),
        "home_team_id": record.get("home_team_id"),
        "away_team_id": record.get("away_team_id"),
        "home_team_name": record.get("home_team_name"),
        "away_team_name": record.get("away_team_name"),
        "stadium": record.get("stadium"),
        "host_city": record.get("host_city"),
        "stage": record.get("stage"),
        "group_id": record.get("group_id"),
        "match_date": record.get("match_date"),
        "status": record.get("status"),
        "home_score": record.get("home_score"),
        "away_score": record.get("away_score"),
        "winner_team_id": record.get("winner_team_id"),
        "source_name": record.get("source_name"),
        "source_entity_id": record.get("source_entity_id"),
        "raw_source_file": record.get("raw_source_file"),
    }


def _standard_match_event_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": record.get("event_id"),
        "match_id": record.get("match_id"),
        "event_minute": record.get("event_minute"),
        "event_type": record.get("event_type"),
        "team_id": record.get("team_id"),
        "player_id": record.get("player_id"),
        "player_name": record.get("player_name"),
        "related_player_id": record.get("related_player_id"),
        "related_player_name": record.get("related_player_name"),
        "event_detail": record.get("event_detail"),
        "source_name": record.get("source_name"),
        "source_entity_id": record.get("source_entity_id"),
        "raw_source_file": record.get("raw_source_file"),
    }


def _append_match_status_event(factory: EventFactory, events: list[dict[str, Any]], record: dict[str, Any]) -> None:
    payload = _standard_match_payload(record)
    status = normalize_match_status(record.get("status"))
    entity_id = str(payload["match_id"])
    if status == "LIVE":
        events.append(
            factory.create_match_started(
                source_name=str(record["source_name"]),
                entity_id=entity_id,
                match_id=str(record["match_id"]),
                payload=payload,
                source_timestamp=record.get("match_date"),
            )
        )
    elif status == "FINISHED":
        events.append(
            factory.create_match_finished(
                source_name=str(record["source_name"]),
                entity_id=entity_id,
                match_id=str(record["match_id"]),
                payload=payload,
                source_timestamp=record.get("match_date"),
            )
        )
    else:
        events.append(
            factory.create_match_scheduled(
                source_name=str(record["source_name"]),
                entity_id=entity_id,
                match_id=str(record["match_id"]),
                payload=payload,
                source_timestamp=record.get("match_date"),
            )
        )

def _normalize_team_ref(*candidates: object) -> str | None:
    for value in candidates:
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "none" and text.lower() != "nan":
            return text
    return None


def _extend_events_from_api_payloads(factory: EventFactory, events: list[dict[str, Any]]) -> None:
    api_football_records = normalize_api_football_payloads(
        fixtures_payload=load_api_football_payload("fixtures_raw.json"),
        teams_payload=load_api_football_payload("teams_raw.json"),
        standings_payload=load_api_football_payload("standings_raw.json"),
        events_payload=load_api_football_payload("events_raw.json"),
    )
    for team in api_football_records["teams"]:
        record = team.model_dump()
        events.append(
            factory.create_team_registered(
                source_name="api_football",
                entity_id=str(record["team_id"]),
                team_id=str(record["team_id"]),
                payload=_standard_team_payload(record),
                source_timestamp=None,
            )
        )
    for match in api_football_records["matches"]:
        _append_match_status_event(factory, events, match.model_dump())
    for match_event in api_football_records["match_events"]:
        record = match_event.model_dump()
        events.append(
            factory.create_match_event(
                source_name="api_football",
                entity_id=str(record["event_id"]),
                event_type=str(record["event_type"]),
                match_id=str(record["match_id"]),
                team_id=record.get("team_id"),
                player_id=record.get("player_id"),
                payload=_standard_match_event_payload(record),
                source_timestamp=None,
            )
        )
    _write_run(
        "api_football_normalization",
        "completed",
        len(api_football_records["teams"]) + len(api_football_records["matches"]) + len(api_football_records["match_events"]),
        None,
        detail=f"errors={len(api_football_records['errors'])}",
    )

    football_data_records = normalize_football_data_payloads(
        matches_payload=load_football_data_payload("matches_raw.json"),
        teams_payload=load_football_data_payload("teams_raw.json"),
        standings_payload=load_football_data_payload("standings_raw.json"),
    )
    for team in football_data_records["teams"]:
        record = team.model_dump()
        events.append(
            factory.create_team_registered(
                source_name="football_data",
                entity_id=str(record["team_id"]),
                team_id=str(record["team_id"]),
                payload=_standard_team_payload(record),
                source_timestamp=None,
            )
        )
    _write_run(
        "football_data_normalization",
        "completed",
        len(football_data_records["teams"]) + len(football_data_records["matches"]) + len(football_data_records["match_events"]),
        None,
        detail=f"errors={len(football_data_records['errors'])}",
    )
    for match in football_data_records["matches"]:
        _append_match_status_event(factory, events, match.model_dump())
    for match_event in football_data_records["match_events"]:
        record = match_event.model_dump()
        events.append(
            factory.create_match_event(
                source_name="football_data",
                entity_id=str(record["event_id"]),
                event_type=str(record["event_type"]),
                match_id=str(record["match_id"]),
                team_id=record.get("team_id"),
                player_id=record.get("player_id"),
                payload=_standard_match_event_payload(record),
                source_timestamp=None,
            )
        )


def build_dim_team() -> Path:
    """Build dim_team from TEAM_REGISTERED events."""
    frame = read_csv(EVENT_LOG_DIR / "event_log.csv")
    team_events = frame[frame["event_type"] == "TEAM_REGISTERED"].copy()
    rows: list[dict[str, Any]] = []
    for _, event in team_events.iterrows():
        payload = json.loads(event["payload_json"])
        rows.append(
            {
                "team_id": payload.get("team_id"),
                "team_name": payload.get("team_name"),
                "country_code": payload.get("country_code"),
                "confederation": payload.get("confederation"),
                "group_id": payload.get("group_id"),
                "is_host": bool(payload.get("is_host", False)),
                "source_name": event["source_name"],
                "source_entity_id": payload.get("source_entity_id"),
            }
        )

    dim_team = pd.DataFrame(rows)
    if dim_team.empty:
        dim_team = pd.DataFrame(
            columns=[
                "team_id",
                "team_name",
                "country_code",
                "confederation",
                "group_id",
                "is_host",
                "source_name",
                "source_entity_id",
            ]
        )
    dim_team["source_priority"] = dim_team["source_name"].map(SOURCE_PRIORITY).fillna(999)
    dim_team = dim_team.sort_values(["team_id", "source_priority"]).drop_duplicates("team_id", keep="first")
    dim_team = dim_team.drop(columns=["source_priority"]).sort_values("team_id")
    output_path = CANONICAL_DIR / "dim_team.csv"
    write_csv(output_path, dim_team)
    return output_path


def build_dim_player() -> Path:
    """Build dim_player from PLAYER_REGISTERED events and observed match participants."""
    events = read_csv(EVENT_LOG_DIR / "event_log.csv")
    rows: list[dict[str, Any]] = []

    player_events = events[events["event_type"] == "PLAYER_REGISTERED"]
    for _, event in player_events.iterrows():
        payload = json.loads(event["payload_json"])
        rows.append(
            {
                "player_id": payload.get("player_id"),
                "player_name": payload.get("player_name"),
                "team_id": payload.get("team_id"),
                "position": payload.get("position"),
                "shirt_number": payload.get("shirt_number"),
                "birth_date": payload.get("birth_date"),
                "club": payload.get("club"),
                "source_name": event["source_name"],
                "source_entity_id": payload.get("source_entity_id"),
            }
        )

    match_events = events[events["event_type"].isin(MATCH_EVENT_TYPES)]
    for _, event in match_events.iterrows():
        payload = json.loads(event["payload_json"])
        for player_field in ["player_id", "related_player_id"]:
            player_id = payload.get(player_field)
            if not player_id:
                continue
            rows.append(
                {
                    "player_id": player_id,
                    "player_name": payload.get("player_name") if player_field == "player_id" else payload.get("related_player_name") or player_id,
                    "team_id": payload.get("team_id"),
                    "position": None,
                    "shirt_number": None,
                    "birth_date": None,
                    "club": None,
                    "source_name": event["source_name"],
                    "source_entity_id": payload.get("source_entity_id"),
                }
            )

    dim_player = pd.DataFrame(rows)
    if dim_player.empty:
        dim_player = pd.DataFrame(
            columns=[
                "player_id",
                "player_name",
                "team_id",
                "position",
                "shirt_number",
                "birth_date",
                "club",
                "source_name",
                "source_entity_id",
            ]
        )
    dim_player["source_priority"] = dim_player["source_name"].map(SOURCE_PRIORITY).fillna(999)
    dim_player = dim_player.sort_values(["player_id", "source_priority"]).drop_duplicates("player_id", keep="first")
    dim_player = dim_player.drop(columns=["source_priority"]).sort_values("player_id")
    output_path = CANONICAL_DIR / "dim_player.csv"
    write_csv(output_path, dim_player)
    return output_path


def build_fact_match() -> Path:
    """Build fact_match from scheduled and finished events."""
    events = read_csv(EVENT_LOG_DIR / "event_log.csv")
    lifecycle = events[events["event_type"].isin({"MATCH_SCHEDULED", "MATCH_STARTED", "MATCH_FINISHED"})].copy()

    rows: list[dict[str, Any]] = []
    status_rank = {"MATCH_SCHEDULED": 0, "MATCH_STARTED": 1, "MATCH_FINISHED": 2}
    for _, event in lifecycle.iterrows():
        payload = json.loads(event["payload_json"])
        rows.append(
            {
                "match_id": payload.get("match_id"),
                "tournament_id": payload.get("tournament_id"),
                "competition_name": payload.get("competition_name"),
                "competition_year": payload.get("competition_year"),
                "home_team_id": payload.get("home_team_id"),
                "away_team_id": payload.get("away_team_id"),
                "home_team_name": payload.get("home_team_name"),
                "away_team_name": payload.get("away_team_name"),
                "stadium": payload.get("stadium"),
                "host_city": payload.get("host_city"),
                "stage": payload.get("stage"),
                "group_id": payload.get("group_id"),
                "match_date": payload.get("match_date"),
                "status": payload.get("status") or "SCHEDULED",
                "home_score": payload.get("home_score"),
                "away_score": payload.get("away_score"),
                "winner_team_id": payload.get("winner_team_id"),
                "source_name": event["source_name"],
                "source_entity_id": payload.get("source_entity_id"),
                "event_rank": status_rank.get(event["event_type"], 0),
            }
        )

    fact_match = pd.DataFrame(rows)
    if fact_match.empty:
        fact_match = pd.DataFrame(
            columns=[
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
            ]
        )

    fact_match["source_priority"] = fact_match["source_name"].map(SOURCE_PRIORITY).fillna(999)
    fact_match = fact_match.sort_values(["match_id", "source_priority", "event_rank"], ascending=[True, True, False])
    max_event_rank = fact_match.groupby("match_id", dropna=False)["event_rank"].max().rename("max_event_rank")
    fact_match = fact_match.groupby("match_id", dropna=False, as_index=False).first()
    fact_match = fact_match.merge(max_event_rank, on="match_id", how="left")
    fact_match.loc[fact_match["max_event_rank"] == 2, "status"] = "FINISHED"
    fact_match.loc[fact_match["max_event_rank"] == 1, "status"] = "LIVE"
    fact_match = fact_match.drop(columns=["source_priority", "event_rank", "max_event_rank"], errors="ignore").sort_values("match_id")
    output_path = CANONICAL_DIR / "fact_match.csv"
    write_csv(output_path, fact_match)
    return output_path


def build_fact_match_event() -> Path:
    """Build fact_match_event from match events in the event log."""
    events = read_csv(EVENT_LOG_DIR / "event_log.csv")
    rows: list[dict[str, Any]] = []
    for _, event in events[events["event_type"].isin(MATCH_EVENT_TYPES)].iterrows():
        payload = json.loads(event["payload_json"])
        rows.append(
            {
                "event_id": event["event_id"],
                "match_id": event["match_id"],
                "event_minute": payload.get("event_minute"),
                "event_type": event["event_type"],
                "team_id": payload.get("team_id"),
                "player_id": payload.get("player_id"),
                "player_name": payload.get("player_name"),
                "related_player_id": payload.get("related_player_id"),
                "related_player_name": payload.get("related_player_name"),
                "event_detail": payload.get("event_detail"),
                "source_name": event["source_name"],
                "source_entity_id": payload.get("source_entity_id"),
            }
        )

    fact_match_event = pd.DataFrame(rows)
    if fact_match_event.empty:
        fact_match_event = pd.DataFrame(
            columns=[
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
            ]
        )
    fact_match_event = fact_match_event.sort_values(["match_id", "event_minute", "event_id"])
    output_path = CANONICAL_DIR / "fact_match_event.csv"
    write_csv(output_path, fact_match_event)
    return output_path


def build_canonical_model() -> list[Path]:
    """Build all canonical tables."""
    return [
        build_dim_team(),
        build_dim_player(),
        build_fact_match(),
        build_fact_match_event(),
    ]


def calculate_group_standings() -> Path:
    """Calculate basic group standings using finished group matches."""
    rules = _rules()
    tournament = rules.get("tournament", {})
    points_for_win = int(tournament.get("points_for_win", 3))
    points_for_draw = int(tournament.get("points_for_draw", 1))
    points_for_loss = int(tournament.get("points_for_loss", 0))

    dim_team = read_csv(CANONICAL_DIR / "dim_team.csv")
    fact_match = read_csv(CANONICAL_DIR / "fact_match.csv")

    team_lookup = (
        dim_team.sort_values("team_id")
        .drop_duplicates("team_id", keep="first")
        .set_index("team_id")["team_name"]
        .to_dict()
    )

    group_matches = _group_match_candidates(fact_match)
    finished_matches = _finished_group_matches(fact_match)
    standings_keys = finished_matches[["tournament_id", "competition_year", "group_id"]].drop_duplicates()

    if standings_keys.empty:
        output_path = STATE_DIR / "state_group_standings.csv"
        write_csv(
            output_path,
            pd.DataFrame(
                columns=[
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
                ]
            ),
        )
        return output_path

    relevant_group_matches = group_matches.merge(
        standings_keys,
        on=["tournament_id", "competition_year", "group_id"],
        how="inner",
    )
    relevant_finished_matches = finished_matches.merge(
        standings_keys,
        on=["tournament_id", "competition_year", "group_id"],
        how="inner",
    )

    participants: list[dict[str, Any]] = []
    for _, match in relevant_group_matches.iterrows():
        for team_id in [match["home_team_id"], match["away_team_id"]]:
            participants.append(
                {
                    "tournament_id": match["tournament_id"],
                    "competition_year": int(match["competition_year"]),
                    "group_id": match["group_id"],
                    "team_id": team_id,
                    "team_name": team_lookup.get(str(team_id), str(team_id)),
                    "matches_played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "goal_difference": 0,
                    "points": 0,
                    "rank_in_group": None,
                }
            )

    standings = pd.DataFrame(participants)
    standings = standings.drop_duplicates(
        ["tournament_id", "competition_year", "group_id", "team_id"], keep="first"
    )
    standings = standings.set_index(["tournament_id", "competition_year", "group_id", "team_id"])

    for _, match in relevant_finished_matches.iterrows():
        key_base = (match["tournament_id"], int(match["competition_year"]), match["group_id"])
        home_team_id = match["home_team_id"]
        away_team_id = match["away_team_id"]
        home_key = (*key_base, home_team_id)
        away_key = (*key_base, away_team_id)
        if home_key not in standings.index or away_key not in standings.index:
            continue

        home_score = int(match["home_score"])
        away_score = int(match["away_score"])

        standings.at[home_key, "matches_played"] += 1
        standings.at[away_key, "matches_played"] += 1
        standings.at[home_key, "goals_for"] += home_score
        standings.at[home_key, "goals_against"] += away_score
        standings.at[away_key, "goals_for"] += away_score
        standings.at[away_key, "goals_against"] += home_score

        if home_score > away_score:
            standings.at[home_key, "wins"] += 1
            standings.at[away_key, "losses"] += 1
            standings.at[home_key, "points"] += points_for_win
            standings.at[away_key, "points"] += points_for_loss
        elif away_score > home_score:
            standings.at[away_key, "wins"] += 1
            standings.at[home_key, "losses"] += 1
            standings.at[away_key, "points"] += points_for_win
            standings.at[home_key, "points"] += points_for_loss
        else:
            standings.at[home_key, "draws"] += 1
            standings.at[away_key, "draws"] += 1
            standings.at[home_key, "points"] += points_for_draw
            standings.at[away_key, "points"] += points_for_draw

    standings["goal_difference"] = standings["goals_for"] - standings["goals_against"]
    standings = standings.reset_index(drop=False)
    standings = standings.sort_values(
        ["tournament_id", "competition_year", "group_id", "points", "goal_difference", "goals_for", "team_name"],
        ascending=[True, True, True, False, False, False, True],
    )
    standings["rank_in_group"] = standings.groupby(["tournament_id", "competition_year", "group_id"]).cumcount() + 1
    output_path = STATE_DIR / "state_group_standings.csv"
    write_csv(output_path, standings)
    return output_path


def calculate_qualification_status() -> pd.DataFrame:
    """Create a simple qualification status view from group standings."""
    standings = read_csv(STATE_DIR / "state_group_standings.csv")
    if standings.empty:
        return pd.DataFrame(columns=["group_id", "team_id", "team_name", "qualification_status"])

    standings["qualification_status"] = standings["rank_in_group"].apply(
        lambda rank: "QUALIFIED" if pd.notna(rank) and int(rank) <= 2 else "IN_CONTENTION"
    )
    return standings[["group_id", "team_id", "team_name", "qualification_status"]]


def build_tournament_state() -> list[Path]:
    """Build tournament state outputs."""
    standings_path = calculate_group_standings()
    qualification = calculate_qualification_status()
    qualification_path = STATE_DIR / "state_qualification_status.csv"
    write_csv(qualification_path, qualification)
    return [standings_path, qualification_path]


def build_mart_group_standings() -> Path:
    standings = read_csv(STATE_DIR / "state_group_standings.csv")
    output_path = MARTS_DIR / "mart_group_standings.csv"
    write_csv(output_path, standings)
    return output_path


def build_mart_match_center() -> Path:
    matches = read_csv(CANONICAL_DIR / "fact_match.csv")
    teams = read_csv(CANONICAL_DIR / "dim_team.csv")[["team_id", "team_name"]]
    home_lookup = teams.rename(columns={"team_id": "home_team_id", "team_name": "home_team_name_dim"})
    away_lookup = teams.rename(columns={"team_id": "away_team_id", "team_name": "away_team_name_dim"})
    merged = matches.merge(home_lookup, on="home_team_id", how="left")
    merged = merged.merge(away_lookup, on="away_team_id", how="left")
    if "home_team_name" in merged.columns:
        merged["home_team_name"] = merged["home_team_name"].fillna(merged["home_team_name_dim"])
    else:
        merged["home_team_name"] = merged["home_team_name_dim"]
    if "away_team_name" in merged.columns:
        merged["away_team_name"] = merged["away_team_name"].fillna(merged["away_team_name_dim"])
    else:
        merged["away_team_name"] = merged["away_team_name_dim"]
    merged = merged.drop(columns=["home_team_name_dim", "away_team_name_dim"], errors="ignore")
    output_path = MARTS_DIR / "mart_match_center.csv"
    write_csv(output_path, merged)
    return output_path


def build_mart_team_performance() -> Path:
    standings = read_csv(STATE_DIR / "state_group_standings.csv")
    merged = (
        standings.groupby(["tournament_id", "competition_year", "team_id", "team_name"], dropna=False)
        .agg(
            groups_played=("group_id", "nunique"),
            matches_played=("matches_played", "sum"),
            wins=("wins", "sum"),
            draws=("draws", "sum"),
            losses=("losses", "sum"),
            goals_for=("goals_for", "sum"),
            goals_against=("goals_against", "sum"),
            goal_difference=("goal_difference", "sum"),
            points=("points", "sum"),
            best_rank_in_group=("rank_in_group", "min"),
        )
        .reset_index()
    )
    output_path = MARTS_DIR / "mart_team_performance.csv"
    write_csv(output_path, merged)
    return output_path


def build_analytics_marts() -> list[Path]:
    """Build analytics marts for downstream serving."""
    return [
        build_mart_group_standings(),
        build_mart_match_center(),
        build_mart_team_performance(),
    ]


def build_source_contribution_report() -> Path:
    """Summarize source contribution across canonical and event layers."""
    event_log = read_csv(EVENT_LOG_DIR / "event_log.csv")
    dim_team = read_csv(CANONICAL_DIR / "dim_team.csv")
    fact_match = read_csv(CANONICAL_DIR / "fact_match.csv")
    fact_match_event = read_csv(CANONICAL_DIR / "fact_match_event.csv")

    sources = sorted(
        set(event_log.get("source_name", pd.Series(dtype=str)).dropna().astype(str))
        | set(dim_team.get("source_name", pd.Series(dtype=str)).dropna().astype(str))
        | set(fact_match.get("source_name", pd.Series(dtype=str)).dropna().astype(str))
        | set(fact_match_event.get("source_name", pd.Series(dtype=str)).dropna().astype(str))
    )

    rows: list[dict[str, Any]] = []
    for source_name in sources:
        source_matches = fact_match[fact_match["source_name"].astype(str) == source_name]
        rows.append(
            {
                "source_name": source_name,
                "teams_count": int(dim_team[dim_team["source_name"].astype(str) == source_name]["team_id"].nunique()),
                "matches_count": int(source_matches["match_id"].nunique()),
                "match_events_count": int(
                    fact_match_event[fact_match_event["source_name"].astype(str) == source_name]["event_id"].nunique()
                ),
                "finished_matches_count": int((source_matches["status"].astype(str) == "FINISHED").sum()),
                "scheduled_matches_count": int((source_matches["status"].astype(str) == "SCHEDULED").sum()),
                "live_matches_count": int((source_matches["status"].astype(str) == "LIVE").sum()),
                "event_log_count": int(event_log[event_log["source_name"].astype(str) == source_name]["event_id"].nunique()),
            }
        )

    report = pd.DataFrame(rows)
    output_path = QUALITY_DIR / "source_contribution_report.csv"
    write_csv(output_path, report)
    return output_path


def run_quality_checks() -> dict[str, object]:
    """Validate generated outputs and persist a quality report."""
    report = validate_pipeline_outputs(
        event_log_path=EVENT_LOG_DIR / "event_log.csv",
        dim_team_path=CANONICAL_DIR / "dim_team.csv",
        fact_match_path=CANONICAL_DIR / "fact_match.csv",
        fact_match_event_path=CANONICAL_DIR / "fact_match_event.csv",
        standings_path=STATE_DIR / "state_group_standings.csv",
        source_contribution_path=QUALITY_DIR / "source_contribution_report.csv",
        ingestion_runs_path=RAW_INGESTION_METADATA_DIR / "ingestion_runs.json",
        allowed_event_types=EVENT_TYPES,
    )
    write_json(QUALITY_DIR / "quality_report.json", report)
    return report


def build_pipeline_summary(quality_report: dict[str, object]) -> dict[str, int]:
    """Collect final pipeline counts for operator-facing output."""
    event_log = read_csv(EVENT_LOG_DIR / "event_log.csv")
    dim_team = read_csv(CANONICAL_DIR / "dim_team.csv")
    fact_match = read_csv(CANONICAL_DIR / "fact_match.csv")
    fact_match_event = read_csv(CANONICAL_DIR / "fact_match_event.csv")
    standings = read_csv(STATE_DIR / "state_group_standings.csv")
    finished_group_matches = _finished_group_matches(fact_match)
    report_summary = quality_report.get("summary", {})
    return {
        "events_created": int(len(event_log)),
        "teams": int(len(dim_team)),
        "matches": int(len(fact_match)),
        "match_events": int(len(fact_match_event)),
        "standings_rows": int(len(standings)),
        "tournaments_found": int(standings["tournament_id"].nunique()) if not standings.empty else 0,
        "finished_group_stage_matches_used": int(len(finished_group_matches)),
        "groups_generated": int(standings[["tournament_id", "group_id"]].drop_duplicates().shape[0]) if not standings.empty else 0,
        "quality_checks_passed": int(report_summary.get("passed_checks", 0)),
        "quality_checks_failed": int(report_summary.get("failed_checks", 0)),
    }


def run_pipeline(include_api: bool = True) -> dict[str, Any]:
    """Run the full local MVP pipeline."""
    organize_data_folders()
    initialize_ingestion_run_log()
    sample_summary = ingest_local_sample_files()
    openfootball_summary = ingest_openfootball()
    fjelstul_summary = ingest_fjelstul()
    api_messages = ingest_api_sources(include_api=include_api)
    event_log_path = build_event_log()
    canonical_paths = build_canonical_model()
    state_paths = build_tournament_state()
    mart_paths = build_analytics_marts()
    source_contribution_report_path = build_source_contribution_report()
    quality_report = run_quality_checks()
    pipeline_summary = build_pipeline_summary(quality_report)
    return {
        "sample_summary": sample_summary,
        "openfootball_summary": openfootball_summary,
        "fjelstul_summary": fjelstul_summary,
        "api_messages": api_messages,
        "event_log_path": event_log_path,
        "canonical_paths": canonical_paths,
        "state_paths": state_paths,
        "mart_paths": mart_paths,
        "source_contribution_report_path": source_contribution_report_path,
        "quality_report": quality_report,
        "pipeline_summary": pipeline_summary,
    }
