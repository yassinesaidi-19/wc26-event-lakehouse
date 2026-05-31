"""Build mart_group_standings."""

from __future__ import annotations

from wc2026.pipeline import build_mart_group_standings


def main() -> None:
    output_path = build_mart_group_standings()
    print(f"Wrote mart_group_standings to {output_path}")


if __name__ == "__main__":
    main()
