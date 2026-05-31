"""Shared normalized schemas for source-specific tournament records."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StandardTeam(BaseModel):
    """Normalized team record produced by source-specific parsers."""

    model_config = ConfigDict(extra="allow")

    team_id: str
    team_name: str | None = None
    country_code: str | None = None
    confederation: str | None = None
    group_id: str | None = None
    is_host: bool = False
    source_name: str
    source_entity_id: str
    raw_source_file: str | None = None


class StandardMatch(BaseModel):
    """Normalized match record produced by source-specific parsers."""

    model_config = ConfigDict(extra="allow")

    match_id: str
    tournament_id: str | None = None
    competition_name: str | None = None
    competition_year: int | None = None
    home_team_id: str | None = None
    away_team_id: str | None = None
    home_team_name: str | None = None
    away_team_name: str | None = None
    stadium: str | None = None
    host_city: str | None = None
    stage: str | None = None
    group_id: str | None = None
    match_date: str | None = None
    status: str = "UNKNOWN"
    home_score: int | None = None
    away_score: int | None = None
    winner_team_id: str | None = None
    source_name: str
    source_entity_id: str
    raw_source_file: str | None = None


class StandardMatchEvent(BaseModel):
    """Normalized match-event record produced by source-specific parsers."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    match_id: str
    event_minute: int | None = None
    event_type: str
    team_id: str | None = None
    player_id: str | None = None
    player_name: str | None = None
    related_player_id: str | None = None
    related_player_name: str | None = None
    event_detail: str | None = None
    source_name: str
    source_entity_id: str
    raw_source_file: str | None = None
