# Databricks notebook source
#
# Purpose:
# - explain how the serving layer shifts from local CSV readers to Databricks SQL tables/views
# - document the handoff from Delta-backed marts to SQL warehouses, BI tools, or downstream services
# - keep FastAPI and Streamlit as local examples while Databricks SQL becomes the warehouse-native serving path

print("Databricks notebook 06_serving_tables: document serving over Databricks SQL.")
