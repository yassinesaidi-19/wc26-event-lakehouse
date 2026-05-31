"""Smoke checks for local dashboard and API serving."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

REQUIRED_PROCESSED_FILES = [
    ROOT_DIR / "data" / "processed" / "marts" / "mart_group_standings.csv",
    ROOT_DIR / "data" / "processed" / "marts" / "mart_match_center.csv",
    ROOT_DIR / "data" / "processed" / "marts" / "mart_team_performance.csv",
    ROOT_DIR / "data" / "quality" / "quality_report.json",
    ROOT_DIR / "data" / "quality" / "source_contribution_report.csv",
]


@dataclass(frozen=True)
class CheckResult:
    """One serving check result."""

    name: str
    passed: bool
    detail: str


def _pass(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, passed=True, detail=detail)


def _fail(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, passed=False, detail=detail)


def check_required_outputs() -> list[CheckResult]:
    """Verify the processed serving files exist."""
    results: list[CheckResult] = []
    for path in REQUIRED_PROCESSED_FILES:
        relative_path = path.relative_to(ROOT_DIR)
        if path.exists():
            results.append(_pass(f"file:{relative_path}", "present"))
        else:
            results.append(_fail(f"file:{relative_path}", "missing"))
    return results


def check_dashboard_module() -> CheckResult:
    """Import the Streamlit dashboard safely and verify its entrypoint."""
    dashboard_path = ROOT_DIR / "dashboard" / "streamlit_app.py"
    if not dashboard_path.exists():
        return _fail("dashboard", f"missing file: {dashboard_path.relative_to(ROOT_DIR)}")

    try:
        module = importlib.import_module("dashboard.streamlit_app")
    except Exception as exc:  # pragma: no cover - surfaced as a runtime failure report
        return _fail("dashboard", f"import failed: {exc}")

    if not hasattr(module, "main"):
        return _fail("dashboard", "dashboard.streamlit_app imported, but no main() function was found")

    return _pass("dashboard", "dashboard.streamlit_app imported successfully")


def check_api_module() -> tuple[CheckResult, Any | None]:
    """Import api.main and verify its FastAPI app exists."""
    try:
        module = importlib.import_module("api.main")
    except Exception as exc:  # pragma: no cover - surfaced as a runtime failure report
        return _fail("api-module", f"import failed: {exc}"), None

    app = getattr(module, "app", None)
    if app is None:
        return _fail("api-module", "api.main imported, but app was not found"), None

    return _pass("api-module", "api.main imported and app exists"), app


def check_api_endpoints(app: Any) -> list[CheckResult]:
    """Call the main FastAPI serving endpoints."""
    results: list[CheckResult] = []
    with TestClient(app) as client:
        for path in ["/health", "/summary", "/tournaments"]:
            response = client.get(path)
            if response.status_code == 200:
                results.append(_pass(f"endpoint:{path}", f"status {response.status_code}"))
            else:
                results.append(_fail(f"endpoint:{path}", f"status {response.status_code}: {response.text}"))
    return results


def run_checks() -> list[CheckResult]:
    """Run all local serving checks and return the full report."""
    results = check_required_outputs()
    results.append(check_dashboard_module())

    api_result, app = check_api_module()
    results.append(api_result)
    if app is not None:
        results.extend(check_api_endpoints(app))

    return results


def print_report(results: list[CheckResult]) -> None:
    """Print a clear pass/fail report."""
    print("Local serving check report")
    print("=" * 26)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name} - {result.detail}")

    passed_count = sum(1 for result in results if result.passed)
    print("-" * 26)
    print(f"Passed: {passed_count}/{len(results)}")


def main() -> int:
    """Execute the local serving smoke checks."""
    results = run_checks()
    print_report(results)
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
