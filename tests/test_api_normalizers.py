"""Unit tests for API normalizers and shared status mapping."""

from __future__ import annotations

import unittest

import pandas as pd

from run_pipeline import run_pipeline
from wc2026.paths import QUALITY_DIR


class APINormalizerTestCase(unittest.TestCase):
    """Validate source-specific API normalization behavior."""

    def test_status_mapping(self) -> None:
        from wc2026.status import normalize_match_status

        self.assertEqual(normalize_match_status("FT"), "FINISHED")
        self.assertEqual(normalize_match_status("TIMED"), "SCHEDULED")
        self.assertEqual(normalize_match_status("1H"), "LIVE")
        self.assertEqual(normalize_match_status("POSTPONED"), "POSTPONED")
        self.assertEqual(normalize_match_status("CANC"), "CANCELLED")
        self.assertEqual(normalize_match_status("mystery"), "UNKNOWN")

    def test_api_football_normalizer(self) -> None:
        from ingestion.normalizers.normalize_api_football import normalize_api_football_payloads

        payload = {
            "response": [
                {
                    "fixture": {
                        "id": 111,
                        "date": "2022-11-20T16:00:00+00:00",
                        "status": {"short": "FT", "long": "Match Finished"},
                        "venue": {"name": "Alpha Stadium", "city": "Doha"},
                    },
                    "league": {"id": 1, "name": "World Cup", "season": 2022, "round": "Group Stage - 1"},
                    "teams": {
                        "home": {"id": 1569, "name": "Qatar"},
                        "away": {"id": 2382, "name": "Ecuador"},
                    },
                    "goals": {"home": 0, "away": 2},
                    "score": {"fulltime": {"home": 0, "away": 2}},
                }
            ]
        }
        teams_payload = {
            "response": [
                {
                    "team": {"id": 1569, "code": "QAT", "name": "Qatar"},
                    "venue": {"name": "Alpha Stadium", "city": "Doha"},
                }
            ]
        }

        normalized = normalize_api_football_payloads(fixtures_payload=payload, teams_payload=teams_payload)

        self.assertEqual(len(normalized["matches"]), 1)
        self.assertEqual(len(normalized["teams"]), 1)
        match = normalized["matches"][0]
        self.assertEqual(match.match_id, "API_FOOTBALL_MATCH_111")
        self.assertEqual(match.source_entity_id, "111")
        self.assertEqual(match.status, "FINISHED")
        self.assertEqual(match.home_team_id, "API_FOOTBALL_TEAM_1569")
        self.assertEqual(match.away_team_id, "API_FOOTBALL_TEAM_2382")
        self.assertEqual(match.winner_team_id, "API_FOOTBALL_TEAM_2382")

    def test_football_data_normalizer(self) -> None:
        from ingestion.normalizers.normalize_football_data import normalize_football_data_payloads

        matches_payload = {
            "competition": {"id": 2000, "name": "FIFA World Cup", "code": "WC"},
            "matches": [
                {
                    "id": 537327,
                    "utcDate": "2026-06-11T19:00:00Z",
                    "status": "TIMED",
                    "stage": "GROUP_STAGE",
                    "group": "GROUP_A",
                    "season": {"startDate": "2026-06-11"},
                    "homeTeam": {"id": 769, "name": "Mexico", "tla": "MEX"},
                    "awayTeam": {"id": 774, "name": "South Africa", "tla": "RSA"},
                    "score": {"fullTime": {"home": None, "away": None}},
                }
            ],
        }
        teams_payload = {
            "teams": [
                {
                    "id": 769,
                    "name": "Mexico",
                    "tla": "MEX",
                    "area": {"name": "Mexico"},
                }
            ]
        }

        normalized = normalize_football_data_payloads(matches_payload=matches_payload, teams_payload=teams_payload)

        self.assertEqual(len(normalized["matches"]), 1)
        self.assertEqual(len(normalized["teams"]), 1)
        self.assertEqual(len(normalized["match_events"]), 0)
        match = normalized["matches"][0]
        self.assertEqual(match.match_id, "FOOTBALL_DATA_MATCH_537327")
        self.assertEqual(match.source_entity_id, "537327")
        self.assertEqual(match.status, "SCHEDULED")
        self.assertEqual(match.group_id, "GROUP_A")
        self.assertEqual(match.home_team_id, "FOOTBALL_DATA_TEAM_769")

    def test_pipeline_writes_source_contribution_report(self) -> None:
        run_pipeline(include_api=False)
        report_path = QUALITY_DIR / "source_contribution_report.csv"
        report = pd.read_csv(report_path)

        self.assertTrue(report_path.exists())
        self.assertIn("source_name", report.columns)
        self.assertIn("event_log_count", report.columns)
        self.assertTrue(set(["sample", "openfootball", "fjelstul"]).issubset(set(report["source_name"])))


if __name__ == "__main__":
    unittest.main()
