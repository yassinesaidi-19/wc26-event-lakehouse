"""Run quality checks for generated tournament outputs."""

from __future__ import annotations

from wc2026.pipeline import run_quality_checks


def main() -> None:
    run_quality_checks()
    print("Quality checks passed.")


if __name__ == "__main__":
    main()
