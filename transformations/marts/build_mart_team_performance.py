"""Build mart_team_performance."""

from __future__ import annotations

from wc2026.pipeline import build_mart_team_performance


def main() -> None:
    output_path = build_mart_team_performance()
    print(f"Wrote mart_team_performance to {output_path}")


if __name__ == "__main__":
    main()
