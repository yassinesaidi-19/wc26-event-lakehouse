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


def spark_readable_path(path: Path) -> str:
    """Return a Spark-readable path for local, workspace, and DBFS files."""
    resolved = path.resolve()

    path_text = str(resolved)

    if path_text.startswith("/Workspace/"):
        return f"file:{path_text}"

    if path_text.startswith("/dbfs/"):
        return path_text.replace("/dbfs/", "dbfs:/", 1)

    return path_text


def _read_local_payload_for_spark(spark: Any, path: Path, file_format: str) -> Any:
    """Read local processed CSV/JSON output with Python, then convert to Spark DataFrame."""
    import pandas as pd

    if not path.exists():
        raise FileNotFoundError(f"Processed output not found: {path}")

    if file_format == "csv":
        pdf = pd.read_csv(path)
        
        if pdf.empty:
            pdf = pd.DataFrame([{
                "source_file": path.name,
                "is_empty": True,
            }])

        for col in pdf.columns:
            if pdf[col].dtype == "object":
                pdf[col] = pdf[col].astype("string")

        return spark.createDataFrame(pdf)

    elif file_format == "json":
        payload = read_json(path)

        if path.name == "quality_report.json" and isinstance(payload, dict):
            rows = [{
                "status": payload.get("status"),
                "checks_passed": payload.get("checks_passed"),
                "checks_failed": payload.get("checks_failed"),
                "generated_at": payload.get("generated_at"),
                "source_file": path.name,
            }]
            return spark.createDataFrame(rows)

        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = [payload]
        else:
            rows = [{
                "value": str(payload),
                "source_file": path.name,
            }]

        return spark.createDataFrame(rows)

    raise ValueError(f"Unsupported file format: {file_format}")


def write_delta_table(
    spark: Any,
    *,
    local_path: Path,
    full_table_name: str,
    file_format: str,
    mode: str = "overwrite",
) -> dict[str, object]:
    """Write one local processed output to a Delta table."""
    if not local_path.exists():
        raise FileNotFoundError(f"Processed output not found: {local_path}")

    frame = _read_local_payload_for_spark(spark, local_path, file_format)
    frame.write \
        .format("delta") \
        .mode(mode) \
        .option("overwriteSchema", "true") \
        .saveAsTable(full_table_name)

    return {
        "table_name": full_table_name,
        "local_path": str(local_path),
        "mode": mode,
        "format": file_format,
    }


def write_all_delta_tables(config: dict[str, object], mode: str = "overwrite") -> list[dict[str, object]]:
    """Write every mapped local processed output into Delta tables."""
    spark = get_spark_session()
    targets = build_table_targets(config)

    results: list[dict[str, object]] = []

    for spec in targets.values():
        print(f"Writing {spec['full_name']} from {spec['path']} as {spec['format']}")

        local_path = Path(spec["path"])

        results.append(
            write_delta_table(
                spark,
                local_path=local_path,
                full_table_name=str(spec["full_name"]),
                file_format=str(spec["format"]),
                mode=mode,
            )
        )

    return results
