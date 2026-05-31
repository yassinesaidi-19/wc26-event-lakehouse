"""API-Football client for raw payload ingestion."""

from __future__ import annotations

import os
from pathlib import Path

import requests

from wc2026.io_utils import write_json
from wc2026.paths import RAW_API_FOOTBALL_DIR
from wc2026.project_setup import load_local_env


class APIFootballClient:
    """Fetch raw payloads from API-Football without transforming them."""

    def __init__(self) -> None:
        load_local_env()
        self.api_key = os.getenv("API_FOOTBALL_KEY", "").strip()
        if not self.api_key:
            raise ValueError("Missing API_FOOTBALL_KEY in local environment.")
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {"x-apisports-key": self.api_key}

    def _get(self, endpoint: str, params: dict[str, object]) -> object:
        response = requests.get(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            params=params,
            timeout=30,
        )
        if response.status_code != 200:
            raise ValueError(f"API-Football request failed with status {response.status_code} for {endpoint}")
        return response.json()

    def fetch_all(self) -> list[Path]:
        """Fetch fixtures, teams, and standings raw payloads."""
        # Update the competition identifiers below when official 2026 API identifiers are stable.
        fixtures = self._get("/fixtures", {"league": 1, "season": 2022})
        teams = self._get("/teams", {"league": 1, "season": 2022})
        standings = self._get("/standings", {"league": 1, "season": 2022})
        outputs = [
            RAW_API_FOOTBALL_DIR / "fixtures_raw.json",
            RAW_API_FOOTBALL_DIR / "teams_raw.json",
            RAW_API_FOOTBALL_DIR / "standings_raw.json",
        ]
        for path, payload in zip(outputs, [fixtures, teams, standings], strict=True):
            write_json(path, payload)
        return outputs
