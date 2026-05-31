"""football-data.org client for raw payload ingestion."""

from __future__ import annotations

import os
from pathlib import Path

import requests

from wc2026.io_utils import write_json
from wc2026.paths import RAW_FOOTBALL_DATA_DIR
from wc2026.project_setup import load_local_env


class FootballDataClient:
    """Fetch raw payloads from football-data.org without transforming them."""

    def __init__(self) -> None:
        load_local_env()
        self.api_key = os.getenv("FOOTBALL_DATA_KEY", "").strip()
        if not self.api_key:
            raise ValueError("Missing FOOTBALL_DATA_KEY in local environment.")
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": self.api_key}

    def _get(self, endpoint: str) -> object:
        response = requests.get(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            timeout=30,
        )
        if response.status_code != 200:
            raise ValueError(f"football-data.org request failed with status {response.status_code} for {endpoint}")
        return response.json()

    def fetch_all(self) -> list[Path]:
        """Fetch matches, teams, and standings raw payloads."""
        # Replace `WC` below when official 2026 competition identifiers or custom scopes are required.
        matches = self._get("/competitions/WC/matches")
        teams = self._get("/competitions/WC/teams")
        standings = self._get("/competitions/WC/standings")
        outputs = [
            RAW_FOOTBALL_DATA_DIR / "matches_raw.json",
            RAW_FOOTBALL_DATA_DIR / "teams_raw.json",
            RAW_FOOTBALL_DATA_DIR / "standings_raw.json",
        ]
        for path, payload in zip(outputs, [matches, teams, standings], strict=True):
            write_json(path, payload)
        return outputs
