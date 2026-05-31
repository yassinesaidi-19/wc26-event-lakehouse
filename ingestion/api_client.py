"""Local placeholder client for file-based source ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wc2026.io_utils import read_json_records


class LocalJsonClient:
    """A tiny client abstraction that can later be replaced by API-backed sources."""

    def read_records(self, path: Path) -> list[dict[str, Any]]:
        return read_json_records(path)
