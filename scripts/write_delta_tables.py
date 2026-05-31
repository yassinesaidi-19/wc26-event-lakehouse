"""CLI entrypoint for writing local processed outputs to Delta tables."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from wc2026.databricks.config import load_databricks_config
from wc2026.databricks.delta_writer import spark_available, write_all_delta_tables


def main() -> int:
    config = load_databricks_config()
    if not spark_available():
        print("Spark is not available. Skipping Delta table writes. Local CSV/JSON pipeline remains unchanged.")
        return 0

    results = write_all_delta_tables(config=config, mode="overwrite")
    print("Delta table writes completed:")
    for row in results:
        print(f"{row['table_name']} <- {row['local_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
