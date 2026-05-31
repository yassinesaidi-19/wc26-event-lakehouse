"""Delta Lake writer helpers that are safe to import without Spark."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from wc2026.io_utils import read_json
from wc2026.databricks.table_names import build_table_targets


def spark_available() -> bool:
    """Return True when pyspark is importable in the current environment."""
    if os.getenv("WC2026_DISABLE_SPARK", "").strip() == "1":
        return False
    return importlib.util.find_spec("pyspark") is not None


def get_spark_session(app_name: str = "WorldCup2026DeltaWriter") -> Any:
    """Create a Spark session lazily."""
    if not spark_available():
        raise RuntimeError("Spark is not available in this environment.")
    from pyspark.sql import SparkSession

    return SparkSession.builder.appName(app_name).getOrCreate()


def _read_local_payload_for_spark(spark: Any, path: Path, file_format: str) -> Any:
    if file_format == "csv":
        return spark.read.option("header", True).option("inferSchema", True).csv(str(path))
    payload = read_json(path)
    if isinstance(payload, list):
        rows = payload
    else:
        rows = [payload]
    return spark.createDataFrame(rows)


def write_delta_table(
    spark: Any,
    *,
    local_path: Path,
    full_table_name: str,
    file_format: str,
    mode: str = "overwrite",
) -> dict[str, object]:
    """Write one local processed output to a Delta table."""
    frame = _read_local_payload_for_spark(spark, local_path, file_format)
    frame.write.format("delta").mode(mode).saveAsTable(full_table_name)
    return {"table_name": full_table_name, "local_path": str(local_path), "mode": mode}


def write_all_delta_tables(config: dict[str, object], mode: str = "overwrite") -> list[dict[str, object]]:
    """Write every mapped local processed output into Delta tables."""
    spark = get_spark_session()
    targets = build_table_targets(config)
    results: list[dict[str, object]] = []
    for spec in targets.values():
        results.append(
            write_delta_table(
                spark,
                local_path=Path(spec["path"]),
                full_table_name=str(spec["full_name"]),
                file_format=str(spec["format"]),
                mode=mode,
            )
        )
    return results
