# Databricks notebook source
#
# Purpose:
# - calculate tournament rules and state from canonical Delta tables
# - write `state_group_standings` and `state_qualification_status`
# - preserve the current ranking logic and tournament/year isolation rules

print("Databricks notebook 04_state_engine: write state Delta tables.")
