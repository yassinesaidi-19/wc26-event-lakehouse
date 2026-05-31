"""Build mart_match_center."""

from __future__ import annotations

from wc2026.pipeline import build_mart_match_center


def main() -> None:
    output_path = build_mart_match_center()
    print(f"Wrote mart_match_center to {output_path}")


if __name__ == "__main__":
    main()
