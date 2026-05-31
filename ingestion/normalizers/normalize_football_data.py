"""Normalize football-data.org raw payloads into standardized intermediate records."""

from __future__ import annotations

import re
from typing import Any

from wc2026.schemas import StandardMatch, StandardMatchEvent, StandardTeam
from wc2026.status import normalize_match_status


def _safe_list(payload: Any, key: str) -> list[Any]:
    if not isinstance(payload, dict):
        return []
    values = payload.get(key, [])
    return values if isinstance(values, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "null"}:
        return None
    return text


def _clean_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _prefixed_id(prefix: str, source_entity_id: object) -> str | None:
    entity = _clean_string(source_entity_id)
    if entity is None:
        return None
    return f"{prefix}{entity}"


def _extract_year(*values: object) -> int | None:
    for value in values:
        text = _clean_string(value)
        if text is None:
            continue
        match = re.search(r"(19|20)\d{2}", text)
        if match:
            return int(match.group(0))
    return None


def _winner_team_id(home_score: object, away_score: object, home_team_id: str | None, away_team_id: str | None) -> str | None:
    home_value = _clean_int(home_score)
    away_value = _clean_int(away_score)
    if home_value is None or away_value is None:
        return None
    if home_value > away_value:
        return home_team_id
    if away_value > home_value:
        return away_team_id
    return None


def normalize_football_data_payloads(
    *,
    matches_payload: Any = None,
    teams_payload: Any = None,
    standings_payload: Any = None,
) -> dict[str, list[Any]]:
    """Normalize football-data.org payloads defensively and never raise on bad input."""
    normalized: dict[str, list[Any]] = {"teams": [], "matches": [], "match_events": [], "errors": []}
    standings_group_lookup: dict[str, str] = {}

    try:
        for group_wrapper in _safe_list(standings_payload, "standings"):
            group_dict = _safe_dict(group_wrapper)
            group_id = _clean_string(group_dict.get("group"))
            for row in _safe_list(group_dict, "table"):
                row_dict = _safe_dict(row)
                team = _safe_dict(row_dict.get("team"))
                team_id = _prefixed_id("FOOTBALL_DATA_TEAM_", team.get("id"))
                if team_id is not None:
                    standings_group_lookup[team_id] = group_id or standings_group_lookup.get(team_id)
    except Exception as exc:
        normalized["errors"].append(f"football_data standings normalization warning: {exc}")

    try:
        for item in _safe_list(teams_payload, "teams"):
            item_dict = _safe_dict(item)
            source_entity_id = _clean_string(item_dict.get("id"))
            team_id = _prefixed_id("FOOTBALL_DATA_TEAM_", item_dict.get("id"))
            if team_id is None or source_entity_id is None:
                continue
            normalized["teams"].append(
                StandardTeam(
                    team_id=team_id,
                    team_name=_clean_string(item_dict.get("name")),
                    country_code=_clean_string(item_dict.get("tla")) or _clean_string(_safe_dict(item_dict.get("area")).get("code")),
                    confederation=_clean_string(_safe_dict(item_dict.get("area")).get("name")),
                    group_id=standings_group_lookup.get(team_id),
                    is_host=_clean_string(item_dict.get("name")) in {"Mexico", "Canada", "United States"},
                    source_name="football_data",
                    source_entity_id=source_entity_id,
                    raw_source_file="teams_raw.json",
                )
            )
    except Exception as exc:
        normalized["errors"].append(f"football_data team normalization warning: {exc}")

    try:
        competition = _safe_dict(matches_payload).get("competition", {}) if isinstance(matches_payload, dict) else {}
        for item in _safe_list(matches_payload, "matches"):
            item_dict = _safe_dict(item)
            source_entity_id = _clean_string(item_dict.get("id"))
            match_id = _prefixed_id("FOOTBALL_DATA_MATCH_", item_dict.get("id"))
            if match_id is None or source_entity_id is None:
                continue
            home_team = _safe_dict(item_dict.get("homeTeam"))
            away_team = _safe_dict(item_dict.get("awayTeam"))
            score = _safe_dict(item_dict.get("score"))
            full_time = _safe_dict(score.get("fullTime"))
            competition_year = _extract_year(_safe_dict(item_dict.get("season")).get("startDate"), item_dict.get("utcDate"))
            home_team_id = _prefixed_id("FOOTBALL_DATA_TEAM_", home_team.get("id"))
            away_team_id = _prefixed_id("FOOTBALL_DATA_TEAM_", away_team.get("id"))
            home_score = _clean_int(full_time.get("home"))
            away_score = _clean_int(full_time.get("away"))
            normalized["matches"].append(
                StandardMatch(
                    match_id=match_id,
                    tournament_id=f"FOOTBALL_DATA-{_clean_string(_safe_dict(competition).get('id'))}-{competition_year}",
                    competition_name=_clean_string(_safe_dict(competition).get("name")),
                    competition_year=competition_year,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_team_name=_clean_string(home_team.get("name")),
                    away_team_name=_clean_string(away_team.get("name")),
                    stadium=None,
                    host_city=None,
                    stage=_clean_string(item_dict.get("stage")),
                    group_id=_clean_string(item_dict.get("group")),
                    match_date=_clean_string(item_dict.get("utcDate")),
                    status=normalize_match_status(item_dict.get("status")),
                    home_score=home_score,
                    away_score=away_score,
                    winner_team_id=_winner_team_id(home_score, away_score, home_team_id, away_team_id),
                    source_name="football_data",
                    source_entity_id=source_entity_id,
                    raw_source_file="matches_raw.json",
                )
            )
    except Exception as exc:
        normalized["errors"].append(f"football_data match normalization warning: {exc}")

    # The free football-data.org plan may not expose detailed match events.
    return normalized
