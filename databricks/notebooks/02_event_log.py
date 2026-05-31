# Databricks notebook source
#
# Purpose:
# - build the immutable tournament event log from the normalized source layer
# - write `data/processed/event_log/event_log.csv` equivalent records into
#   `wc26_lakehouse.event_log.event_log`
# - keep the event-log semantics unchanged while Delta replaces CSV as the durable table layer

print("Databricks notebook 02_event_log: write event log Delta table.")
