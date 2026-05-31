# Databricks Migration

## Goal

The local MVP stays file-based and fully runnable without cloud credentials. The Databricks path is additive: it maps the already verified processed outputs into Unity Catalog Delta tables and defines a Databricks Workflow structure around them.

## Two Execution Modes

### Local MVP

Writes durable local outputs as CSV and JSON:

- `data/processed/event_log/event_log.csv`
- `data/processed/canonical/*.csv`
- `data/processed/state/*.csv`
- `data/processed/marts/*.csv`
- `data/quality/quality_report.json`
- `data/quality/source_contribution_report.csv`

### Databricks Version

Writes equivalent outputs as Delta tables under Unity Catalog:

- `wc26_lakehouse.event_log.event_log`
- `wc26_lakehouse.canonical.dim_team`
- `wc26_lakehouse.canonical.dim_player`
- `wc26_lakehouse.canonical.fact_match`
- `wc26_lakehouse.canonical.fact_match_event`
- `wc26_lakehouse.state.state_group_standings`
- `wc26_lakehouse.state.state_qualification_status`
- `wc26_lakehouse.marts.mart_group_standings`
- `wc26_lakehouse.marts.mart_match_center`
- `wc26_lakehouse.marts.mart_team_performance`
- `wc26_lakehouse.quality.source_contribution_report`
- `wc26_lakehouse.quality.quality_report`

## Direct Mapping

- `data/processed/event_log` -> `wc26_lakehouse.event_log.event_log`
- `data/processed/canonical` -> `wc26_lakehouse.canonical.*`
- `data/processed/state` -> `wc26_lakehouse.state.*`
- `data/processed/marts` -> `wc26_lakehouse.marts.*`
- `data/quality` -> `wc26_lakehouse.quality.*`

## Local-Safe Delta Writer

The repo now includes:

- `configs/databricks.yml`
- `wc2026/databricks/config.py`
- `wc2026/databricks/table_names.py`
- `wc2026/databricks/delta_writer.py`
- `scripts/write_delta_tables.py`

Behavior:

- loads Databricks catalog/schema/table configuration
- detects whether Spark is available
- exits gracefully when Spark is unavailable
- performs overwrite-mode MVP Delta writes when Spark is available

This means Databricks credentials are not required for local tests.

## Workflow Structure

Databricks Workflows orchestrate the notebooks in this order:

1. `01_ingestion`
2. `02_event_log`
3. `03_canonical_model`
4. `04_state_engine`
5. `05_marts_quality`
6. `06_serving_tables`

The bundle and workflow definitions live in:

- `databricks/bundle.yml`
- `databricks/jobs/world_cup_pipeline_job.yml`

## SQL Layer

The SQL scaffolding lives under `databricks/sql/`:

- `create_schemas.sql`
- `create_tables.sql`
- `quality_views.sql`

These files document the intended Unity Catalog layout and basic warehouse-facing views for:

- latest quality status
- source contribution summary
- tournament summary

## Future Direction

The current implementation is a pragmatic migration step, not a full Databricks deployment. The next realistic upgrades would be:

1. replace local raw landing with cloud object storage and Auto Loader
2. run the existing pipeline stages inside Databricks notebooks or Python tasks
3. store secrets in Databricks secret scopes
4. use Delta Lake as the primary durable analytical table layer
5. use Databricks SQL for warehouse-native serving
