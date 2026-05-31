"""CLI entry point for team ingestion."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = next(path for path in Path(__file__).resolve().parents if (path / "wc2026").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wc2026.pipeline import ingest_teams


if __name__ == "__main__":
    output_path = ingest_teams()
    print(f"Wrote raw teams data to {output_path}")
