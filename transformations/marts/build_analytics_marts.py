"""Build all analytics marts."""

from __future__ import annotations

from wc2026.pipeline import build_analytics_marts


def main() -> None:
    output_paths = build_analytics_marts()
    for output_path in output_paths:
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
