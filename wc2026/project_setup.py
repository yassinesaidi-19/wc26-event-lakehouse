"""Project setup and local migration helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path

from wc2026.io_utils import ensure_directory
from wc2026.paths import (
    CANONICAL_DIR,
    DATA_DIR,
    ENV_FILE,
    EVENT_LOG_DIR,
    FJELSTUL_DIR,
    MARTS_DIR,
    OPENFOOTBALL_DIR,
    QUALITY_DIR,
    QUARANTINE_DIR,
    RAW_API_FOOTBALL_DIR,
    RAW_DIR,
    RAW_FOOTBALL_DATA_DIR,
    RAW_INGESTION_METADATA_DIR,
    SAMPLE_DIR,
    STATE_DIR,
)


REQUIRED_DIRS = [
    OPENFOOTBALL_DIR.parent,
    FJELSTUL_DIR.parent,
    SAMPLE_DIR,
    RAW_API_FOOTBALL_DIR,
    RAW_FOOTBALL_DATA_DIR,
    RAW_INGESTION_METADATA_DIR,
    EVENT_LOG_DIR,
    CANONICAL_DIR,
    STATE_DIR,
    MARTS_DIR,
    QUALITY_DIR,
    QUARANTINE_DIR,
]


def load_local_env() -> None:
    """Load local environment variables from .env when present."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        os.environ.setdefault(key, value)


def _move_if_exists(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    ensure_directory(destination.parent)
    if destination.exists():
        return
    source.rename(destination)


def _ensure_env_var_from_file(candidate_paths: list[Path], env_name: str) -> None:
    env_lines: list[str] = []
    if ENV_FILE.exists():
        env_lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    else:
        ENV_FILE.touch()

    if any(line.startswith(f"{env_name}=") for line in env_lines):
        for path in candidate_paths:
            if path.exists():
                _quarantine_secret_file(path)
        return

    for path in candidate_paths:
        if not path.exists():
            continue
        secret = path.read_text(encoding="utf-8").strip()
        if secret:
            with ENV_FILE.open("a", encoding="utf-8") as handle:
                handle.write(f"{env_name}={secret}\n")
        _quarantine_secret_file(path)
        break


def _quarantine_secret_file(path: Path) -> None:
    ensure_directory(QUARANTINE_DIR)
    destination = QUARANTINE_DIR / path.name
    if destination.exists():
        path.unlink()
        return
    path.rename(destination)


def migrate_api_keys() -> None:
    """Move raw API key files into the local .env file without printing them."""
    _ensure_env_var_from_file([RAW_DIR / "api_football.txt"], "API_FOOTBALL_KEY")
    _ensure_env_var_from_file(
        [
            RAW_DIR / "api_football_data.txt",
            RAW_DIR / "api_football data.txt",
        ],
        "FOOTBALL_DATA_KEY",
    )
    load_local_env()


def organize_data_folders() -> None:
    """Create the target folder layout and migrate legacy raw assets."""
    for directory in REQUIRED_DIRS:
        ensure_directory(directory)

    _move_if_exists(RAW_DIR / "worldcup.json-master", OPENFOOTBALL_DIR)
    _move_if_exists(RAW_DIR / "worldcup-master", FJELSTUL_DIR)
    _move_if_exists(RAW_DIR / "fixtures.json", SAMPLE_DIR / "fixtures.json")
    _move_if_exists(RAW_DIR / "teams.json", SAMPLE_DIR / "teams.json")
    _move_if_exists(RAW_DIR / "match_events.json", SAMPLE_DIR / "match_events.json")

    migrate_api_keys()
    _remove_legacy_processed_outputs()


def api_key_exists(env_name: str) -> bool:
    """Return true when a non-empty API key is available locally."""
    load_local_env()
    return bool(os.getenv(env_name, "").strip())


def _remove_legacy_processed_outputs() -> None:
    for file_name in [
        "event_log.json",
        "dim_team.json",
        "fact_match.json",
        "fact_match_event.json",
        "state_group_standings.json",
    ]:
        path = DATA_DIR / "processed" / file_name
        if path.exists():
            path.unlink()
