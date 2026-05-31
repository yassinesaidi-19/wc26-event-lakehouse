"""Source loaders for local files, public datasets, and raw API payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from wc2026.io_utils import read_json, read_json_records, read_yaml
from wc2026.paths import CONFIGS_DIR, FJELSTUL_DIR, OPENFOOTBALL_DIR, RAW_API_FOOTBALL_DIR, RAW_FOOTBALL_DATA_DIR, SAMPLE_DIR


def load_source_definitions() -> dict[str, Any]:
    """Load source definitions from YAML."""
    return read_yaml(CONFIGS_DIR / "sources.yml").get("sources", {})


def _resolve_dataset_root(root: Path) -> Path:
    nested_root = root / root.name
    if nested_root.exists():
        return nested_root
    return root


def explore_dataset_files(root: Path) -> list[str]:
    """List likely CSV and JSON files under a dataset root."""
    resolved = _resolve_dataset_root(root)
    if not resolved.exists():
        return []
    files = [
        path.relative_to(resolved).as_posix()
        for path in resolved.rglob("*")
        if path.is_file() and path.suffix.lower() in {".csv", ".json"}
    ]
    return sorted(files)


def _sample_path(config_key: str, fallback_name: str) -> Path:
    sources = load_source_definitions()
    source_config = sources.get("sample", {})
    relative = source_config.get(config_key)
    if relative:
        candidate = SAMPLE_DIR.parent.parent / relative
        if candidate.exists():
            return candidate
    fallback = SAMPLE_DIR / fallback_name
    if fallback.exists():
        return fallback
    legacy_fallback = SAMPLE_DIR / fallback_name.replace(".json", "_2026_sample.json")
    return legacy_fallback


def load_sample_teams() -> list[dict[str, Any]]:
    return read_json_records(_sample_path("teams_path", "teams.json"))


def load_sample_fixtures() -> list[dict[str, Any]]:
    return read_json_records(_sample_path("fixtures_path", "fixtures.json"))


def load_sample_match_events() -> list[dict[str, Any]]:
    return read_json_records(_sample_path("match_events_path", "match_events.json"))


def load_openfootball_teams() -> list[dict[str, Any]]:
    root = _resolve_dataset_root(OPENFOOTBALL_DIR)
    path = root / "2026" / "worldcup.teams.json"
    if not path.exists():
        return []
    return read_json_records(path)


def load_openfootball_matches() -> list[dict[str, Any]]:
    root = _resolve_dataset_root(OPENFOOTBALL_DIR)
    path = root / "2026" / "worldcup.json"
    if not path.exists():
        return []
    payload = read_json(path)
    if isinstance(payload, dict):
        matches = payload.get("matches", [])
        if isinstance(matches, list):
            return matches
    return []


def load_fjelstul_teams() -> list[dict[str, Any]]:
    root = _resolve_dataset_root(FJELSTUL_DIR)
    path = root / "data-csv" / "teams.csv"
    if not path.exists():
        return []
    return pd.read_csv(path).to_dict(orient="records")


def load_fjelstul_players() -> list[dict[str, Any]]:
    root = _resolve_dataset_root(FJELSTUL_DIR)
    path = root / "data-csv" / "players.csv"
    if not path.exists():
        return []
    return pd.read_csv(path).to_dict(orient="records")


def load_fjelstul_matches() -> list[dict[str, Any]]:
    root = _resolve_dataset_root(FJELSTUL_DIR)
    path = root / "data-csv" / "matches.csv"
    if not path.exists():
        return []
    return pd.read_csv(path).to_dict(orient="records")


def load_api_football_payload(name: str) -> Any:
    path = RAW_API_FOOTBALL_DIR / name
    if not path.exists():
        return None
    return read_json(path)


def load_football_data_payload(name: str) -> Any:
    path = RAW_FOOTBALL_DATA_DIR / name
    if not path.exists():
        return None
    return read_json(path)
