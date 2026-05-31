# Databricks Migration Readiness

## Goal

The local project is intentionally structured so it can migrate to Databricks without redesigning the conceptual architecture.

## Mapping The Local Layers

```text
Local source files and APIs
-> Databricks ingestion notebooks or Jobs tasks
-> Bronze raw storage
-> Event-log normalization
-> Silver canonical model tables
-> Gold state and marts tables
-> Databricks SQL, API services, or dashboards
```

## Suggested Databricks Mapping

### Raw / Bronze

Map the current raw layer into Delta tables or cloud object storage paths such as:

- `bronze.api_football_raw`
- `bronze.football_data_raw`
- `bronze.sample_source_snapshots`
- `bronze.public_source_snapshots`

### Event Log / Silver Entry Point

The current `event_log.csv` is a good candidate for:

- `silver.tournament_event_log`

This is the replayable, immutable layer that should sit between raw ingestion and curated tables.

### Canonical Model / Silver

The canonical outputs map naturally to:

- `silver.dim_team`
- `silver.dim_player`
- `silver.fact_match`
- `silver.fact_match_event`

### State Engine / Gold

Tournament logic should run from canonical match facts and write:

- `gold.state_group_standings`
- `gold.state_qualification_status`

### Marts / Gold

Analytics marts map naturally to:

- `gold.mart_group_standings`
- `gold.mart_match_center`
- `gold.mart_team_performance`

## Why The Current Local Design Helps

The local repo already separates:

- source ingestion
- event normalization
- canonical modeling
- tournament rule execution
- analytics marts
- serving

That means the migration is mostly about execution environment, storage format, and orchestration, not about rethinking the data model from scratch.

## Recommended Migration Steps

1. Replace local CSV outputs with Delta tables.
2. Convert the current pipeline stages into Databricks notebooks or Python tasks.
3. Store secrets in Databricks secret scopes instead of `.env`.
4. Schedule the stages with Databricks Workflows.
5. Add Unity Catalog naming and access controls.
6. Replace file-based serving with Databricks SQL or a downstream service layer.

## Current Skeleton

See the `databricks/` directory for a first-cut structure:

- `databricks/README.md`
- `databricks/jobs/world_cup_pipeline_job.yml`
- `databricks/notebooks/01_ingestion.py`
- `databricks/notebooks/02_event_log.py`
- `databricks/notebooks/03_canonical_model.py`
- `databricks/notebooks/04_state_engine.py`
- `databricks/notebooks/05_marts_quality.py`
