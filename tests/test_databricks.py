"""Tests for the Databricks/Delta execution path."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from importlib import import_module

from run_pipeline import run_pipeline
from wc2026.databricks.config import REQUIRED_SCHEMA_KEYS, REQUIRED_TABLE_KEYS, load_databricks_config
from wc2026.paths import CONFIGS_DIR, ROOT_DIR


class DatabricksPathTestCase(unittest.TestCase):
    """Validate the Databricks scaffolding without requiring Spark or credentials."""

    def test_databricks_config_exists_and_has_required_keys(self) -> None:
        config = load_databricks_config(CONFIGS_DIR / "databricks.yml")
        self.assertEqual(config["catalog"], "wc26_lakehouse")
        self.assertTrue(REQUIRED_SCHEMA_KEYS.issubset(set(config["schemas"])))
        self.assertTrue(REQUIRED_TABLE_KEYS.issubset(set(config["tables"])))

    def test_databricks_helpers_import_without_spark(self) -> None:
        self.assertIsNotNone(import_module("wc2026.databricks.config"))
        self.assertIsNotNone(import_module("wc2026.databricks.delta_writer"))
        self.assertIsNotNone(import_module("wc2026.databricks.table_names"))

    def test_write_delta_tables_exits_gracefully_without_spark(self) -> None:
        env = os.environ.copy()
        env["WC2026_DISABLE_SPARK"] = "1"
        result = subprocess.run(
            [sys.executable, "scripts/write_delta_tables.py"],
            cwd=ROOT_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Spark is not available", result.stdout)

    def test_databricks_notebooks_exist(self) -> None:
        notebook_names = [
            "01_ingestion.py",
            "02_event_log.py",
            "03_canonical_model.py",
            "04_state_engine.py",
            "05_marts_quality.py",
            "06_serving_tables.py",
        ]
        for name in notebook_names:
            self.assertTrue((ROOT_DIR / "databricks" / "notebooks" / name).exists(), name)

    def test_databricks_sql_and_bundle_exist(self) -> None:
        required_paths = [
            ROOT_DIR / "databricks" / "bundle.yml",
            ROOT_DIR / "databricks" / "jobs" / "world_cup_pipeline_job.yml",
            ROOT_DIR / "databricks" / "sql" / "create_schemas.sql",
            ROOT_DIR / "databricks" / "sql" / "create_tables.sql",
            ROOT_DIR / "databricks" / "sql" / "quality_views.sql",
        ]
        for path in required_paths:
            self.assertTrue(path.exists(), str(path))

    def test_local_pipeline_still_passes(self) -> None:
        result = run_pipeline(include_api=False)
        self.assertEqual(result["pipeline_summary"]["quality_checks_failed"], 0)


if __name__ == "__main__":
    unittest.main()
