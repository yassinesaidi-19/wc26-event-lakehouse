# Portfolio Summary

## Short CV Description

Built a local-first World Cup event-driven lakehouse that ingests sample, public, and live football data sources, converts them into an immutable event log and canonical tournament model, computes tournament state, publishes analytics marts, and serves the results through FastAPI and Streamlit.

## Long Portfolio Description

This project is a football analytics data platform built around a tournament-native architecture rather than a generic medallion demo. It starts from multiple source types, including local sample files, public historical datasets, and optional live APIs, then normalizes those records into one immutable event log. From there it builds canonical team, player, match, and match-event tables, applies tournament rules to calculate group standings by tournament and year, publishes analytics marts, and exposes the outputs through a lightweight API and dashboard.

The project also includes quality validation, secret migration into `.env`, tournament-aware historical separation, and a documented migration path to Databricks-style orchestration and storage. The result is both a usable local MVP and a strong portfolio example of data engineering, analytics engineering, and lightweight product serving.

## GitHub README Pitch

World Cup 2026 Event-Driven Tournament Lakehouse is a local-first sports data platform that proves a full architecture: external sources, ingestion, immutable event log, canonical model, tournament state engine, marts, and serving layers. It runs in one command, keeps API secrets out of raw data folders, supports historical tournament separation, and includes both a FastAPI interface and a Streamlit dashboard.

## LinkedIn Post Draft

I built a local-first World Cup event-driven lakehouse to model football tournament data end to end.

The project does more than fetch APIs. It ingests sample files, public historical datasets, and optional live football APIs, converts everything into an immutable event log, resolves canonical team/player/match tables, computes tournament-aware group standings, publishes analytics marts, and serves the results through FastAPI and Streamlit.

It also includes output quality checks, secret handling with `.env`, and a documented path for Databricks migration.

This was a good exercise in turning sports data into a real data-platform architecture instead of stopping at notebooks or raw JSON ingestion.

## Technical Skills Demonstrated

- Python data engineering
- pandas-based data transformation
- event-driven data modeling
- canonical dimensional and fact modeling
- tournament-state computation logic
- REST API delivery with FastAPI
- local analytics UI with Streamlit
- data quality validation
- secret management and repo hygiene
- documentation and architecture communication
- migration planning for Databricks-style lakehouse execution

## Recruiter-Friendly Architecture Explanation

Think of the project as a sports data factory with clear stages.

First, it collects football data from local samples, public downloads, and optional live APIs. Next, it stores the usable records as one standardized event history. Then it turns those events into clean analytical tables for teams, players, matches, and match events. After that, it applies football tournament rules to calculate standings without mixing separate tournaments or years. Finally, it publishes simple business-facing tables and exposes them through an API and dashboard.

That structure makes the project easy to explain, test, and eventually migrate to a larger cloud data platform.
