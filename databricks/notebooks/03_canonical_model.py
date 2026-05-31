# Databricks notebook source
#
# Purpose:
# - build the canonical team, player, match, and match-event tables
# - write them to `wc26_lakehouse.canonical.*`
# - preserve source visibility and tournament-aware separation from the local MVP path

print("Databricks notebook 03_canonical_model: write canonical Delta tables.")
