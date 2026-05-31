"""Serving and local runner regression tests."""

from __future__ import annotations

import importlib
import unittest
from unittest import mock

import pandas as pd

from asgi_client import request
from wc2026.paths import ROOT_DIR
from wc2026.serving import ProcessedOutputsNotReadyError, filter_frame


class LocalServingTestCase(unittest.TestCase):
    """Validate local serving files and graceful API behavior."""

    def test_requirements_include_local_serving_packages(self) -> None:
        requirements_text = (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8").lower()
        for package_name in [
            "pandas",
            "requests",
            "python-dotenv",
            "pydantic",
            "pyyaml",
            "streamlit",
            "fastapi",
            "uvicorn",
        ]:
            self.assertIn(package_name, requirements_text)

    def test_windows_serving_scripts_exist(self) -> None:
        required_paths = [
            ROOT_DIR / "scripts" / "setup_windows.ps1",
            ROOT_DIR / "scripts" / "run_dashboard.ps1",
            ROOT_DIR / "scripts" / "run_api.ps1",
            ROOT_DIR / "scripts" / "check_serving.py",
        ]
        for path in required_paths:
            self.assertTrue(path.exists(), str(path))

    def test_dashboard_entrypoint_exists(self) -> None:
        self.assertTrue((ROOT_DIR / "dashboard" / "streamlit_app.py").exists())

    def test_check_serving_module_imports_safely(self) -> None:
        module = importlib.import_module("scripts.check_serving")
        self.assertTrue(hasattr(module, "run_checks"))

    def test_api_health_degrades_cleanly_when_outputs_are_missing(self) -> None:
        module = importlib.import_module("api.main")
        with mock.patch.object(
            module,
            "build_serving_summary",
            side_effect=ProcessedOutputsNotReadyError("missing processed output"),
        ):
            response = request(module.app, "/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "degraded", "outputs_ready": False})

    def test_api_summary_returns_service_unavailable_when_outputs_are_missing(self) -> None:
        module = importlib.import_module("api.main")
        with mock.patch.object(
            module,
            "build_serving_summary",
            side_effect=ProcessedOutputsNotReadyError("missing processed output"),
        ):
            response = request(module.app, "/summary")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Run python run_pipeline.py first.", response.json()["detail"])

    def test_filter_frame_matches_int_filters_against_float_like_year_columns(self) -> None:
        frame = pd.DataFrame(
            [
                {"tournament_id": "WC-2006", "competition_year": 2006.0},
                {"tournament_id": "WC-2010", "competition_year": 2010.0},
            ]
        )

        filtered = filter_frame(frame, {"competition_year": 2006})

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.iloc[0]["tournament_id"], "WC-2006")

    def test_dashboard_tournament_parser_accepts_float_like_year_strings(self) -> None:
        module = importlib.import_module("dashboard.streamlit_app")

        tournament_id, competition_year = module.parse_selected_tournament("2006.0 | OPENFOOTBALL-WC-2006")

        self.assertEqual(tournament_id, "OPENFOOTBALL-WC-2006")
        self.assertEqual(competition_year, 2006)

    def test_dashboard_tournament_options_render_years_without_decimal_suffix(self) -> None:
        module = importlib.import_module("dashboard.streamlit_app")
        tournaments = pd.DataFrame(
            [
                {"competition_year": 2006.0, "tournament_id": "OPENFOOTBALL-WC-2006"},
                {"competition_year": 2026.0, "tournament_id": "SAMPLE-WC-2026"},
            ]
        )

        options = module.build_tournament_options(tournaments)

        self.assertIn("2006 | OPENFOOTBALL-WC-2006", options)
        self.assertNotIn("2006.0 | OPENFOOTBALL-WC-2006", options)


if __name__ == "__main__":
    unittest.main()
