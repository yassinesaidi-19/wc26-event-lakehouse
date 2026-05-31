"""Run the ingestion layer for local, public, and optional API sources."""

from __future__ import annotations

from wc2026.pipeline import ingest_api_sources, ingest_fjelstul, ingest_local_sample_files, ingest_openfootball
from wc2026.project_setup import organize_data_folders


def run_ingestion(include_api: bool = True) -> None:
    organize_data_folders()
    print("Running sample ingestion...")
    ingest_local_sample_files()
    print("Inspecting openfootball dataset...")
    ingest_openfootball()
    print("Inspecting Fjelstul dataset...")
    ingest_fjelstul()
    print("Running optional API ingestion...")
    for message in ingest_api_sources(include_api=include_api):
        print(message)


if __name__ == "__main__":
    run_ingestion()
