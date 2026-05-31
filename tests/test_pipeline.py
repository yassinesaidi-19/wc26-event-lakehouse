"""End-to-end tests for the local MVP tournament lakehouse pipeline."""

from __future__ import annotations

import json
import unittest
from importlib import import_module

import pandas as pd

from run_pipeline import run_pipeline
from asgi_client import request
from wc2026.paths import CANONICAL_DIR, EVENT_LOG_DIR, MARTS_DIR, QUALITY_DIR, RAW_DIR, ROOT_DIR, STATE_DIR


class PipelineTestCase(unittest.TestCase):
    """Validate the full local pipeline, serving layer, and secret hygiene."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_pipeline(include_api=False)
        cls.event_log = pd.read_csv(EVENT_LOG_DIR / "event_log.csv")
        cls.dim_team = pd.read_csv(CANONICAL_DIR / "dim_team.csv")
        cls.dim_player = pd.read_csv(CANONICAL_DIR / "dim_player.csv")
        cls.fact_match = pd.read_csv(CANONICAL_DIR / "fact_match.csv")
        cls.fact_match_event = pd.read_csv(CANONICAL_DIR / "fact_match_event.csv")
        cls.standings = pd.read_csv(STATE_DIR / "state_group_standings.csv")
        cls.mart_group_standings = pd.read_csv(MARTS_DIR / "mart_group_standings.csv")
        cls.mart_match_center = pd.read_csv(MARTS_DIR / "mart_match_center.csv")
        cls.mart_team_performance = pd.read_csv(MARTS_DIR / "mart_team_performance.csv")
        with (QUALITY_DIR / "quality_report.json").open("r", encoding="utf-8") as handle:
            cls.quality_report = json.load(handle)

    def test_pipeline_outputs_exist(self) -> None:
        self.assertGreaterEqual(len(self.event_log), 14)
        self.assertGreaterEqual(len(self.dim_team), 4)
        self.assertGreaterEqual(len(self.dim_player), 4)
        self.assertGreaterEqual(len(self.fact_match), 3)
        self.assertGreaterEqual(len(self.fact_match_event), 7)
        self.assertGreaterEqual(len(self.standings), 4)
        self.assertGreaterEqual(len(self.mart_group_standings), 4)
        self.assertGreaterEqual(len(self.mart_match_center), 3)
        self.assertGreaterEqual(len(self.mart_team_performance), 4)

    def test_dashboard_input_files_exist(self) -> None:
        required_paths = [
            MARTS_DIR / "mart_group_standings.csv",
            MARTS_DIR / "mart_match_center.csv",
            MARTS_DIR / "mart_team_performance.csv",
            QUALITY_DIR / "quality_report.json",
        ]
        for path in required_paths:
            self.assertTrue(path.exists(), f"Missing dashboard input: {path}")

    def test_quality_report_exists_and_passes(self) -> None:
        self.assertEqual(self.quality_report["status"], "passed")
        self.assertGreaterEqual(len(self.quality_report["checks"]), 1)
        self.assertEqual(int(self.quality_report["summary"]["failed_checks"]), 0)
        self.assertTrue((QUALITY_DIR / "source_contribution_report.csv").exists())

    def test_sample_2026_group_a_standings_remain_isolated(self) -> None:
        sample_standings = self.standings[
            (self.standings["tournament_id"] == "SAMPLE-WC-2026")
            & (self.standings["competition_year"] == 2026)
            & (self.standings["group_id"] == "A")
        ]
        mexico = sample_standings.loc[sample_standings["team_id"] == "MEX"].iloc[0]
        canada = sample_standings.loc[sample_standings["team_id"] == "CAN"].iloc[0]
        usa = sample_standings.loc[sample_standings["team_id"] == "USA"].iloc[0]
        costa_rica = sample_standings.loc[sample_standings["team_id"] == "CRC"].iloc[0]

        self.assertEqual(int(mexico["points"]), 1)
        self.assertEqual(int(canada["points"]), 1)
        self.assertEqual(int(usa["points"]), 0)
        self.assertEqual(int(costa_rica["points"]), 0)
        self.assertEqual(int(mexico["matches_played"]), 1)
        self.assertEqual(int(canada["matches_played"]), 1)

    def test_standings_are_tournament_aware(self) -> None:
        grouped = (
            self.standings.groupby(["tournament_id", "group_id"], dropna=False)["competition_year"]
            .nunique(dropna=True)
            .reset_index(name="year_count")
        )
        self.assertFalse((grouped["year_count"] > 1).any())
        self.assertGreaterEqual(self.result["pipeline_summary"]["tournaments_found"], 2)
        self.assertGreaterEqual(self.result["pipeline_summary"]["groups_generated"], 2)

    def test_api_import_and_health_endpoint(self) -> None:
        module = import_module("api.main")
        response = request(module.app, "/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_api_summary_and_listing_endpoints(self) -> None:
        module = import_module("api.main")

        summary_response = request(module.app, "/summary")
        self.assertEqual(summary_response.status_code, 200)
        self.assertGreaterEqual(summary_response.json()["events_created"], 14)

        tournaments_response = request(module.app, "/tournaments")
        self.assertEqual(tournaments_response.status_code, 200)
        self.assertGreaterEqual(len(tournaments_response.json()), 2)
        self.assertIsInstance(tournaments_response.json()[0]["competition_year"], int)

        standings_response = request(module.app, "/standings", params={"tournament_id": "SAMPLE-WC-2026", "group_id": "A"})
        self.assertEqual(standings_response.status_code, 200)
        self.assertEqual(len(standings_response.json()), 4)

        standings_by_year_response = request(
            module.app,
            "/standings",
            params={"tournament_id": "SAMPLE-WC-2026", "competition_year": 2026, "group_id": "A"},
        )
        self.assertEqual(standings_by_year_response.status_code, 200)
        self.assertEqual(len(standings_by_year_response.json()), 4)

        matches_response = request(module.app, "/matches", params={"tournament_id": "SAMPLE-WC-2026"})
        self.assertEqual(matches_response.status_code, 200)
        self.assertGreaterEqual(len(matches_response.json()), 3)

        teams_response = request(module.app, "/teams", params={"tournament_id": "SAMPLE-WC-2026"})
        self.assertEqual(teams_response.status_code, 200)
        self.assertGreaterEqual(len(teams_response.json()), 4)

        quality_response = request(module.app, "/quality")
        self.assertEqual(quality_response.status_code, 200)
        self.assertEqual(quality_response.json()["status"], "passed")

    def test_no_api_key_text_files_remain_under_raw(self) -> None:
        forbidden = []
        for path in RAW_DIR.rglob("*.txt"):
            path_text = str(path).lower()
            if "api" in path_text or "key" in path_text:
                forbidden.append(path)
        self.assertEqual(forbidden, [])

    def test_env_files_and_gitignore_hygiene(self) -> None:
        gitignore_text = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
        env_example_text = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")

        self.assertIn(".env", gitignore_text)
        self.assertIn("*.env", gitignore_text)
        self.assertIn("API_FOOTBALL_KEY=your_api_football_key_here", env_example_text)
        self.assertIn("FOOTBALL_DATA_KEY=your_football_data_key_here", env_example_text)
        self.assertNotIn("your_real_", env_example_text.lower())

    def test_pipeline_summary_reports_no_quality_failures(self) -> None:
        summary = self.result["pipeline_summary"]
        self.assertGreaterEqual(summary["finished_group_stage_matches_used"], 2)
        self.assertEqual(summary["quality_checks_failed"], 0)


if __name__ == "__main__":
    unittest.main()
