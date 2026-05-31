# Data Model

## Event Log

Path:

```text
data/processed/event_log/event_log.csv
```

Purpose:

- immutable normalized event history
- replayable bridge between heterogeneous sources and canonical tables

Columns:

- `event_id`
- `source_name`
- `event_type`
- `entity_type`
- `entity_id`
- `match_id`
- `team_id`
- `player_id`
- `payload_json`
- `source_timestamp`
- `ingestion_timestamp`
- `batch_id`
- `schema_version`
- `is_valid`
- `error_reason`

API-normalized payloads preserve `source_entity_id` inside `payload_json`.

## Standardized Intermediate Schemas

Used by source-specific normalizers before event-log integration:

### StandardTeam

- `team_id`
- `team_name`
- `country_code`
- `confederation`
- `group_id`
- `is_host`
- `source_name`
- `source_entity_id`

### StandardMatch

- `match_id`
- `tournament_id`
- `competition_name`
- `competition_year`
- `home_team_id`
- `away_team_id`
- `home_team_name`
- `away_team_name`
- `stadium`
- `host_city`
- `stage`
- `group_id`
- `match_date`
- `status`
- `home_score`
- `away_score`
- `winner_team_id`
- `source_name`
- `source_entity_id`

### StandardMatchEvent

- `event_id`
- `match_id`
- `event_minute`
- `event_type`
- `team_id`
- `player_id`
- `player_name`
- `related_player_id`
- `related_player_name`
- `event_detail`
- `source_name`
- `source_entity_id`

## Canonical Model

### dim_team

Path:

```text
data/processed/canonical/dim_team.csv
```

Columns:

- `team_id`
- `team_name`
- `country_code`
- `confederation`
- `group_id`
- `is_host`
- `source_name`
- `source_entity_id`

API team IDs are intentionally source-prefixed. Teams are not merged across sources by name yet.

### dim_player

Path:

```text
data/processed/canonical/dim_player.csv
```

Columns:

- `player_id`
- `player_name`
- `team_id`
- `position`
- `shirt_number`
- `birth_date`
- `club`
- `source_name`
- `source_entity_id`

### fact_match

Path:

```text
data/processed/canonical/fact_match.csv
```

Columns:

- `match_id`
- `tournament_id`
- `competition_name`
- `competition_year`
- `home_team_id`
- `away_team_id`
- `home_team_name`
- `away_team_name`
- `stadium`
- `host_city`
- `stage`
- `group_id`
- `match_date`
- `status`
- `home_score`
- `away_score`
- `winner_team_id`
- `source_name`
- `source_entity_id`

`status` is normalized to:

- `SCHEDULED`
- `LIVE`
- `FINISHED`
- `POSTPONED`
- `CANCELLED`
- `UNKNOWN`

### fact_match_event

Path:

```text
data/processed/canonical/fact_match_event.csv
```

Columns:

- `event_id`
- `match_id`
- `event_minute`
- `event_type`
- `team_id`
- `player_id`
- `player_name`
- `related_player_id`
- `related_player_name`
- `event_detail`
- `source_name`
- `source_entity_id`

Current live-source reality:

- API-Football contributes lifecycle match events now
- football-data.org does not currently contribute detailed match events on the free plan

## Tournament State

The state engine reads canonical `fact_match.csv`.

Only rows with:

- valid `tournament_id`
- valid `competition_year`
- valid `group_id`
- valid `home_team_id`
- valid `away_team_id`
- finished status
- populated scores

are used in group standings.

### state_group_standings

Path:

```text
data/processed/state/state_group_standings.csv
```

Columns:

- `tournament_id`
- `competition_year`
- `group_id`
- `team_id`
- `team_name`
- `matches_played`
- `wins`
- `draws`
- `losses`
- `goals_for`
- `goals_against`
- `goal_difference`
- `points`
- `rank_in_group`

Ranking logic:

1. points descending
2. goal difference descending
3. goals for descending
4. team name ascending

## Analytics Marts

### mart_group_standings

- current schema mirrors `state_group_standings.csv`

### mart_match_center

Built from canonical `fact_match` plus resolved team names.

Key columns:

- `match_id`
- `tournament_id`
- `competition_name`
- `competition_year`
- `home_team_id`
- `away_team_id`
- `home_team_name`
- `away_team_name`
- `stage`
- `group_id`
- `match_date`
- `status`
- `home_score`
- `away_score`
- `winner_team_id`
- `source_name`
- `source_entity_id`

### mart_team_performance

Tournament-aware team aggregation.

Columns:

- `tournament_id`
- `competition_year`
- `team_id`
- `team_name`
- `groups_played`
- `matches_played`
- `wins`
- `draws`
- `losses`
- `goals_for`
- `goals_against`
- `goal_difference`
- `points`
- `best_rank_in_group`
