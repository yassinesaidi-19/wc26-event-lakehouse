# Databricks notebook source
#
# Purpose:
# - explain how the existing local ingestion layer maps to Databricks
# - land raw source files and API payloads into bronze storage or Unity Catalog-backed external locations
# - keep the current Python ingestion logic reusable while Databricks Workflows orchestrate execution
# - document Auto Loader as the future path for continuously arriving source files
#
# Suggested execution:
# 1. Reuse the local ingestion functions to validate source availability.
# 2. Persist raw snapshots into bronze Delta tables or cloud object storage.
# 3. Replace local `.env` secret loading with Databricks secret scopes.
# 4. Record ingestion metadata for observability.

print("Databricks notebook 01_ingestion: map local ingestion to bronze/raw landing.")
