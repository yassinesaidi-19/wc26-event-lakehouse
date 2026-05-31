# Architecture

## Overview

This project models football tournaments through a tournament-native data architecture rather than a generic ingestion demo.

```text
External Sources
-> Ingestion Layer
-> Immutable Tournament Event Log
-> Canonical Tournament Data Model
-> Tournament Rules & State Engine
-> Analytics Marts
-> Serving Layer
```

## Layer Details

### External Sources

The source layer mixes:

- local sample 2026 JSON
- downloaded openfootball files
- downloaded Fjelstul historical files
- raw API-Football payloads
- raw football-data.org payloads

### Ingestion Layer

The ingestion layer:

- validates local sample files
- explores downloaded public datasets
- fetches raw API payloads when keys are present
- preserves raw API JSON under `data/raw/`
- keeps secrets out of `data/raw/`
- records ingestion metadata in `data/raw/ingestion_metadata/ingestion_runs.json`

### API Normalization Layer

Before live API data reaches the event log, source-specific normalizers convert raw payloads into standardized intermediate records:

- `StandardTeam`
- `StandardMatch`
- `StandardMatchEvent`

These normalizers live under `ingestion/normalizers/` and use shared schemas in `wc2026/schemas.py`.

This step is defensive by design:

- empty responses are allowed
- missing keys are allowed
- malformed sections do not stop the pipeline
- unsupported source fields are skipped rather than crashing

### Immutable Tournament Event Log

All sources ultimately produce records in:

```text
data/processed/event_log/event_log.csv
```

That event log includes:

- team registration events
- match lifecycle events
- detailed match events where available

API-normalized match records now create lifecycle events based on canonical status:

- `MATCH_SCHEDULED`
- `MATCH_STARTED`
- `MATCH_FINISHED`

### Canonical Tournament Data Model

The event log is resolved into:

- `dim_team.csv`
- `dim_player.csv`
- `fact_match.csv`
- `fact_match_event.csv`

API-normalized source records now contribute directly to canonical teams and matches, and to canonical match events when detailed events are available.

### Tournament Rules & State Engine

The state engine calculates standings from canonical `fact_match.csv`, not from raw API responses.

Only matches with:

- valid tournament identity
- valid group identity
- valid team identities
- finished-equivalent status
- populated scores

are used for standings.

Historical tournaments remain separated by `tournament_id` and `competition_year`, so no source variant is mixed with another tournament.

### Analytics Marts

The marts publish:

- `mart_group_standings.csv`
- `mart_match_center.csv`
- `mart_team_performance.csv`

These outputs are consumer-facing and source-transparent.

### Serving Layer

The serving layer stays thin:

- `dashboard/streamlit_app.py`
- `api/main.py`

It reads processed outputs rather than recomputing logic.

## Operational Transparency

Two quality-side outputs make source behavior visible:

- `data/quality/quality_report.json`
- `data/quality/source_contribution_report.csv`

That makes it clear when live APIs contributed real canonical data and when they contributed zero usable records without fabricating results.
