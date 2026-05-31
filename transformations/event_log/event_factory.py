"""Factory for consistent immutable tournament event records."""

from __future__ import annotations

import json

from wc2026.models import EventRecord


class EventFactory:
    """Build typed event records across heterogeneous source systems."""

    def __init__(self, batch_id: str, ingestion_timestamp: str, schema_version: str = "1.0") -> None:
        self.batch_id = batch_id
        self.ingestion_timestamp = ingestion_timestamp
        self.schema_version = schema_version

    @staticmethod
    def _normalize_optional_string(value: object) -> str | None:
        if value is None:
            return None
        string_value = str(value).strip()
        if not string_value or string_value.lower() == "nan":
            return None
        return string_value

    def create_event(
        self,
        *,
        source_name: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        match_id: str | None,
        team_id: str | None,
        player_id: str | None,
        payload: dict[str, object],
        source_timestamp: str | None,
    ) -> dict[str, object]:
        record = EventRecord(
            event_id=f"{source_name}:{event_type}:{entity_id}",
            source_name=source_name,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            match_id=self._normalize_optional_string(match_id),
            team_id=self._normalize_optional_string(team_id),
            player_id=self._normalize_optional_string(player_id),
            payload_json=json.dumps(payload, sort_keys=True),
            source_timestamp=self._normalize_optional_string(source_timestamp),
            ingestion_timestamp=self.ingestion_timestamp,
            batch_id=self.batch_id,
            schema_version=self.schema_version,
            is_valid=True,
            error_reason=None,
        )
        return record.model_dump()

    def create_team_registered(
        self,
        *,
        source_name: str,
        entity_id: str,
        team_id: str,
        payload: dict[str, object],
        source_timestamp: str | None,
    ) -> dict[str, object]:
        return self.create_event(
            source_name=source_name,
            event_type="TEAM_REGISTERED",
            entity_type="TEAM",
            entity_id=entity_id,
            match_id=None,
            team_id=team_id,
            player_id=None,
            payload=payload,
            source_timestamp=source_timestamp,
        )

    def create_player_registered(
        self,
        *,
        source_name: str,
        entity_id: str,
        player_id: str,
        payload: dict[str, object],
        source_timestamp: str | None,
    ) -> dict[str, object]:
        return self.create_event(
            source_name=source_name,
            event_type="PLAYER_REGISTERED",
            entity_type="PLAYER",
            entity_id=entity_id,
            match_id=None,
            team_id=payload.get("team_id") if isinstance(payload.get("team_id"), str) else None,
            player_id=player_id,
            payload=payload,
            source_timestamp=source_timestamp,
        )

    def create_match_scheduled(
        self,
        *,
        source_name: str,
        entity_id: str,
        match_id: str,
        payload: dict[str, object],
        source_timestamp: str | None,
    ) -> dict[str, object]:
        return self.create_event(
            source_name=source_name,
            event_type="MATCH_SCHEDULED",
            entity_type="MATCH",
            entity_id=entity_id,
            match_id=match_id,
            team_id=None,
            player_id=None,
            payload=payload,
            source_timestamp=source_timestamp,
        )

    def create_match_started(
        self,
        *,
        source_name: str,
        entity_id: str,
        match_id: str,
        payload: dict[str, object],
        source_timestamp: str | None,
    ) -> dict[str, object]:
        return self.create_event(
            source_name=source_name,
            event_type="MATCH_STARTED",
            entity_type="MATCH",
            entity_id=entity_id,
            match_id=match_id,
            team_id=None,
            player_id=None,
            payload=payload,
            source_timestamp=source_timestamp,
        )

    def create_match_finished(
        self,
        *,
        source_name: str,
        entity_id: str,
        match_id: str,
        payload: dict[str, object],
        source_timestamp: str | None,
    ) -> dict[str, object]:
        return self.create_event(
            source_name=source_name,
            event_type="MATCH_FINISHED",
            entity_type="MATCH",
            entity_id=entity_id,
            match_id=match_id,
            team_id=None,
            player_id=None,
            payload=payload,
            source_timestamp=source_timestamp,
        )

    def create_match_event(
        self,
        *,
        source_name: str,
        entity_id: str,
        event_type: str,
        match_id: str,
        team_id: str | None,
        player_id: str | None,
        payload: dict[str, object],
        source_timestamp: str | None,
    ) -> dict[str, object]:
        return self.create_event(
            source_name=source_name,
            event_type=event_type,
            entity_type="MATCH_EVENT",
            entity_id=entity_id,
            match_id=match_id,
            team_id=team_id,
            player_id=player_id,
            payload=payload,
            source_timestamp=source_timestamp,
        )

    def create_standing_updated(
        self,
        *,
        source_name: str,
        entity_id: str,
        team_id: str | None,
        payload: dict[str, object],
        source_timestamp: str | None,
    ) -> dict[str, object]:
        return self.create_event(
            source_name=source_name,
            event_type="STANDING_UPDATED",
            entity_type="STANDING",
            entity_id=entity_id,
            match_id=None,
            team_id=team_id,
            player_id=None,
            payload=payload,
            source_timestamp=source_timestamp,
        )
