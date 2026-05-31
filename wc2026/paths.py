"""Project path helpers for the tournament lakehouse."""

from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIGS_DIR = ROOT_DIR / "configs"
DATA_DIR = ROOT_DIR / "data"

EXTERNAL_DIR = DATA_DIR / "external"
OPENFOOTBALL_DIR = EXTERNAL_DIR / "openfootball" / "worldcup.json-master"
FJELSTUL_DIR = EXTERNAL_DIR / "fjelstul" / "worldcup-master"

SAMPLE_DIR = DATA_DIR / "sample"
RAW_DIR = DATA_DIR / "raw"
RAW_API_FOOTBALL_DIR = RAW_DIR / "api_football"
RAW_FOOTBALL_DATA_DIR = RAW_DIR / "football_data"
RAW_INGESTION_METADATA_DIR = RAW_DIR / "ingestion_metadata"

PROCESSED_DIR = DATA_DIR / "processed"
EVENT_LOG_DIR = PROCESSED_DIR / "event_log"
CANONICAL_DIR = PROCESSED_DIR / "canonical"
STATE_DIR = PROCESSED_DIR / "state"
MARTS_DIR = PROCESSED_DIR / "marts"

QUALITY_DIR = DATA_DIR / "quality"
QUARANTINE_DIR = DATA_DIR / "quarantine"

DOCS_DIR = ROOT_DIR / "docs"
ENV_FILE = ROOT_DIR / ".env"
