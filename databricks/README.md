# Databricks Delta Path

This directory adds a Databricks-ready execution route on top of the working local MVP.

Local MVP:

- writes CSV and JSON outputs under `data/processed/` and `data/quality/`
- remains the default and fully supported local execution path

Databricks version:

- maps those same processed outputs to Delta tables under Unity Catalog
- uses Databricks Workflows to orchestrate notebook tasks
- uses SQL objects under `databricks/sql/` for catalog, schema, table, and view setup

## Local-Safe Behavior

Databricks credentials are not required for local tests.

- `scripts/write_delta_tables.py` detects whether Spark is available
- if Spark is unavailable, the script prints a clear skip message and exits successfully
- no personal workspace URLs or tokens are stored in the repo

## Table Mapping

- `data/processed/event_log/event_log.csv` -> `wc26_lakehouse.event_log.event_log`
- `data/processed/canonical/*.csv` -> `wc26_lakehouse.canonical.*`
- `data/processed/state/*.csv` -> `wc26_lakehouse.state.*`
- `data/processed/marts/*.csv` -> `wc26_lakehouse.marts.*`
- `data/quality/*.csv|json` -> `wc26_lakehouse.quality.*`

## Files

- `bundle.yml` defines a Databricks Asset Bundle scaffold
- `jobs/world_cup_pipeline_job.yml` defines the workflow tasks
- `notebooks/` contains the stage-by-stage notebook skeletons
- `sql/` contains the catalog, schema, table, and quality-view definitions
