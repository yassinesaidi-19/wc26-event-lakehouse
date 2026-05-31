"""Typed models used across the tournament lakehouse."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class TeamSourceRecord(BaseModel):
    """Team registration source schema."""

    model_config = ConfigDict(extra="allow")

    team_id: str
    team_name: str
    country_code: str
    confederation: str
    group_id: str | None = None
    is_host: bool = False
    source_timestamp: str | None = None


class FixtureSourceRecord(BaseModel):
    """Fixture schedule source schema."""

    model_config = ConfigDict(extra="allow")

    match_id: str
    home_team_id: str
    away_team_id: str
    stadium: str | None = None
    host_city: str | None = None
    stage: str | None = None
    group_id: str | None = None
    match_date: str | None = None
    status: str | None = None
    source_timestamp: str | None = None


class MatchEventSourceRecord(BaseModel):
    """Match event source schema."""

    model_config = ConfigDict(extra="allow")

    source_event_id: str
    match_id: str
    event_type: str
    event_minute: int | None = None
    team_id: str | None = None
    player_id: str | None = None
    related_player_id: str | None = None
    event_detail: str | None = None
    home_score: int | None = None
    away_score: int | None = None
    winner_team_id: str | None = None
    source_timestamp: str | None = None


class EventRecord(BaseModel):
    """Canonical immutable tournament event."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    source_name: str
    event_type: str
    entity_type: str
    entity_id: str
    match_id: str | None = None
    team_id: str | None = None
    player_id: str | None = None
    payload_json: str
    source_timestamp: str | None = None
    ingestion_timestamp: str
    batch_id: str
    schema_version: str
    is_valid: bool
    error_reason: str | None = None


class IngestionRunRecord(BaseModel):
    """Metadata describing a single ingestion stage."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    source_name: str
    status: str
    record_count: int
    output_path: str | None = None
    detail: str | None = None
    started_at: str
    completed_at: str


def model_dump_list(records: list[BaseModel]) -> list[dict[str, Any]]:
    """Convert pydantic records into dictionaries."""
    return [record.model_dump() for record in records]
