# Databricks notebook source
#
# Purpose:
# - build analytics marts from canonical and state Delta tables
# - write quality outputs such as `quality_report` and `source_contribution_report`
# - publish `wc26_lakehouse.marts.*` and `wc26_lakehouse.quality.*`

print("Databricks notebook 05_marts_quality: write marts and quality Delta tables.")
