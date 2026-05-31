# API Response Mapping

This document records the actual raw API response shapes currently stored in the repo and how they map into normalized records.

## API-Football

### `data/raw/api_football/fixtures_raw.json`

Top-level structure:

- dictionary
- keys: `get`, `parameters`, `errors`, `results`, `paging`, `response`
- `response` is a list of fixture objects

Important fields found:

- `fixture.id`
- `fixture.date`
- `fixture.status.short`
- `fixture.status.long`
- `fixture.venue.name`
- `fixture.venue.city`
- `league.id`
- `league.name`
- `league.season`
- `league.round`
- `teams.home.id`
- `teams.home.name`
- `teams.away.id`
- `teams.away.name`
- `goals.home`
- `goals.away`
- `score.fulltime.home`
- `score.fulltime.away`

Mapping target:

- `StandardMatch`

Unsupported or missing fields:

- no guaranteed normalized group ID field, so group is inferred from `league.round` when it contains group-stage text
- no player-level match event detail in this file

### `data/raw/api_football/teams_raw.json`

Top-level structure:

- dictionary
- keys: `get`, `parameters`, `errors`, `results`, `paging`, `response`
- `response` is a list of team wrappers

Important fields found:

- `team.id`
- `team.code`
- `team.name`
- `team.country`
- `venue.name`
- `venue.city`

Mapping target:

- `StandardTeam`

Unsupported or missing fields:

- no stable confederation field in the current payload
- no group ID in the team payload itself

### `data/raw/api_football/standings_raw.json`

Top-level structure:

- dictionary
- keys: `get`, `parameters`, `errors`, `results`, `paging`, `response`
- `response[0].league.standings` is a nested list of group tables

Important fields found:

- `league.id`
- `league.name`
- `league.season`
- `standings[*][*].group`
- `standings[*][*].rank`
- `standings[*][*].points`
- `standings[*][*].team.id`
- `standings[*][*].team.name`
- `standings[*][*].update`

Mapping target:

- team group enrichment during `StandardTeam` normalization

Unsupported or missing fields:

- not currently mapped into canonical standings directly because canonical tournament state is derived from `fact_match`

### `data/raw/api_football/events_raw.json`

Current state:

- not currently fetched by default

Potential mapping target if present:

- `StandardMatchEvent`

Expected event mapping:

- `Goal` -> `GOAL_SCORED`
- `Card` + `Yellow Card` -> `YELLOW_CARD`
- `Card` + `Red Card` -> `RED_CARD`
- `subst` / `Substitution` -> `SUBSTITUTION`

## football-data.org

### `data/raw/football_data/matches_raw.json`

Top-level structure:

- dictionary
- keys: `filters`, `resultSet`, `competition`, `matches`
- `matches` is a list of match objects

Important fields found:

- `id`
- `competition.id`
- `competition.name`
- `competition.code`
- `season.startDate`
- `utcDate`
- `status`
- `stage`
- `group`
- `homeTeam.id`
- `homeTeam.name`
- `homeTeam.tla`
- `awayTeam.id`
- `awayTeam.name`
- `awayTeam.tla`
- `score.fullTime.home`
- `score.fullTime.away`

Mapping target:

- `StandardMatch`

Unsupported or missing fields:

- no stadium field in the current payload
- no city field in the current payload
- no detailed player-level match events in the current plan payload

### `data/raw/football_data/teams_raw.json`

Top-level structure:

- dictionary
- keys: `count`, `filters`, `competition`, `season`, `teams`
- `teams` is a list of team objects

Important fields found:

- `id`
- `name`
- `tla`
- `area.name`
- `venue`
- `squad`

Mapping target:

- `StandardTeam`

Unsupported or missing fields:

- no explicit group field in the team payload
- squad is present but is not yet normalized into a dedicated live-source player pipeline

### `data/raw/football_data/standings_raw.json`

Top-level structure:

- dictionary
- keys: `filters`, `area`, `competition`, `season`, `standings`
- `standings` is a list of group tables

Important fields found:

- `group`
- `stage`
- `table[*].position`
- `table[*].points`
- `table[*].team.id`
- `table[*].team.name`
- `table[*].team.tla`

Mapping target:

- team group enrichment during `StandardTeam` normalization

Unsupported or missing fields:

- no direct detailed event contribution
- not used as the canonical standings source because tournament state is derived from canonical `fact_match`

## General Notes

- raw API responses are preserved as-is under `data/raw/`
- normalized API records are integrated into the event log and canonical tables
- live API emptiness or limited coverage does not break the pipeline
- when no usable live records exist, `data/quality/source_contribution_report.csv` exposes the zero contribution explicitly
