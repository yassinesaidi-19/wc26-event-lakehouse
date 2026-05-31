"""Normalize API-Football raw payloads into standardized intermediate records."""

from __future__ import annotations

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


def _extract_group_and_stage(round_name: object) -> tuple[str | None, str | None]:
    round_text = _clean_string(round_name)
    if round_text is None:
        return None, None
    lowered = round_text.lower()
    if "group" in lowered:
        if "-" in round_text:
            group_part = round_text.split("-", maxsplit=1)[0].strip()
        else:
            group_part = round_text
        group_id = group_part.replace("Group", "").strip() or None
        return group_id, "GROUP_STAGE"
    return None, round_text.upper().replace(" ", "_")


def normalize_api_football_payloads(
    *,
    fixtures_payload: Any = None,
    teams_payload: Any = None,
    standings_payload: Any = None,
    events_payload: Any = None,
) -> dict[str, list[Any]]:
    """Normalize API-Football payloads defensively and never raise on bad input."""
    normalized: dict[str, list[Any]] = {"teams": [], "matches": [], "match_events": [], "errors": []}

    try:
        standings_group_lookup: dict[str, str] = {}
        for league_wrapper in _safe_list(standings_payload, "response"):
            league = _safe_dict(league_wrapper).get("league", {})
            for group_rows in _safe_list(league, "standings"):
                if not isinstance(group_rows, list):
                    continue
                for row in group_rows:
                    row_dict = _safe_dict(row)
                    team = _safe_dict(row_dict.get("team"))
                    team_id = _prefixed_id("API_FOOTBALL_TEAM_", team.get("id"))
                    if team_id is not None:
                        standings_group_lookup[team_id] = _clean_string(row_dict.get("group")) or standings_group_lookup.get(team_id)
    except Exception as exc:
        normalized["errors"].append(f"api_football standings normalization warning: {exc}")

    try:
        for item in _safe_list(teams_payload, "response"):
            item_dict = _safe_dict(item)
            team = _safe_dict(item_dict.get("team"))
            team_entity_id = _clean_string(team.get("id"))
            team_id = _prefixed_id("API_FOOTBALL_TEAM_", team.get("id"))
            if team_id is None or team_entity_id is None:
                continue
            normalized["teams"].append(
                StandardTeam(
                    team_id=team_id,
                    team_name=_clean_string(team.get("name")),
                    country_code=_clean_string(team.get("code")),
                    confederation=_clean_string(team.get("country")),
                    group_id=standings_group_lookup.get(team_id),
                    is_host=_clean_string(team.get("name")) in {"Mexico", "Canada", "United States"},
                    source_name="api_football",
                    source_entity_id=team_entity_id,
                    raw_source_file="teams_raw.json",
                )
            )
    except Exception as exc:
        normalized["errors"].append(f"api_football team normalization warning: {exc}")

    try:
        for item in _safe_list(fixtures_payload, "response"):
            item_dict = _safe_dict(item)
            fixture = _safe_dict(item_dict.get("fixture"))
            league = _safe_dict(item_dict.get("league"))
            teams = _safe_dict(item_dict.get("teams"))
            home_team = _safe_dict(teams.get("home"))
            away_team = _safe_dict(teams.get("away"))
            venue = _safe_dict(fixture.get("venue"))
            score = _safe_dict(item_dict.get("score"))
            score_fulltime = _safe_dict(score.get("fulltime"))
            goals = _safe_dict(item_dict.get("goals"))

            source_entity_id = _clean_string(fixture.get("id"))
            match_id = _prefixed_id("API_FOOTBALL_MATCH_", fixture.get("id"))
            if match_id is None or source_entity_id is None:
                continue

            group_id, stage = _extract_group_and_stage(league.get("round"))
            home_team_id = _prefixed_id("API_FOOTBALL_TEAM_", home_team.get("id"))
            away_team_id = _prefixed_id("API_FOOTBALL_TEAM_", away_team.get("id"))
            home_score = _clean_int(goals.get("home"))
            away_score = _clean_int(goals.get("away"))
            if home_score is None and away_score is None:
                home_score = _clean_int(score_fulltime.get("home"))
                away_score = _clean_int(score_fulltime.get("away"))

            normalized["matches"].append(
                StandardMatch(
                    match_id=match_id,
                    tournament_id=f"API_FOOTBALL-{_clean_string(league.get('id'))}-{_clean_string(league.get('season'))}",
                    competition_name=_clean_string(league.get("name")),
                    competition_year=_clean_int(league.get("season")),
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_team_name=_clean_string(home_team.get("name")),
                    away_team_name=_clean_string(away_team.get("name")),
                    stadium=_clean_string(venue.get("name")),
                    host_city=_clean_string(venue.get("city")),
                    stage=stage,
                    group_id=group_id,
                    match_date=_clean_string(fixture.get("date")),
                    status=normalize_match_status(_safe_dict(fixture.get("status")).get("short"), _safe_dict(fixture.get("status")).get("long")),
                    home_score=home_score,
                    away_score=away_score,
                    winner_team_id=_winner_team_id(home_score, away_score, home_team_id, away_team_id),
                    source_name="api_football",
                    source_entity_id=source_entity_id,
                    raw_source_file="fixtures_raw.json",
                )
            )
    except Exception as exc:
        normalized["errors"].append(f"api_football fixture normalization warning: {exc}")

    try:
        event_type_map = {
            ("GOAL", None): "GOAL_SCORED",
            ("CARD", "YELLOW CARD"): "YELLOW_CARD",
            ("CARD", "RED CARD"): "RED_CARD",
            ("SUBST", None): "SUBSTITUTION",
            ("SUBSTITUTION", None): "SUBSTITUTION",
        }
        for item in _safe_list(events_payload, "response"):
            item_dict = _safe_dict(item)
            type_name = _clean_string(item_dict.get("type"))
            detail_name = _clean_string(item_dict.get("detail"))
            event_type = event_type_map.get(((type_name or "").upper(), (detail_name or "").upper() if detail_name else None))
            if event_type is None and (type_name or "").upper() == "GOAL":
                event_type = "GOAL_SCORED"
            if event_type is None:
                continue
            match_id = _prefixed_id("API_FOOTBALL_MATCH_", item_dict.get("fixture", {}).get("id"))
            source_entity_id = _clean_string(item_dict.get("id")) or _clean_string(item_dict.get("elapsed")) or "unknown"
            if match_id is None:
                continue
            team = _safe_dict(item_dict.get("team"))
            player = _safe_dict(item_dict.get("player"))
            assist = _safe_dict(item_dict.get("assist"))
            normalized["match_events"].append(
                StandardMatchEvent(
                    event_id=f"API_FOOTBALL_EVENT_{source_entity_id}_{len(normalized['match_events']) + 1}",
                    match_id=match_id,
                    event_minute=_clean_int(item_dict.get("elapsed")),
                    event_type=event_type,
                    team_id=_prefixed_id("API_FOOTBALL_TEAM_", team.get("id")),
                    player_id=_prefixed_id("API_FOOTBALL_PLAYER_", player.get("id")),
                    player_name=_clean_string(player.get("name")),
                    related_player_id=_prefixed_id("API_FOOTBALL_PLAYER_", assist.get("id")),
                    related_player_name=_clean_string(assist.get("name")),
                    event_detail=detail_name or type_name,
                    source_name="api_football",
                    source_entity_id=source_entity_id,
                    raw_source_file="events_raw.json",
                )
            )
    except Exception as exc:
        normalized["errors"].append(f"api_football event normalization warning: {exc}")

    return normalized
