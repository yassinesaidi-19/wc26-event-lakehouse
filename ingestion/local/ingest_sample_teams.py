"""Inspect sample team source records."""

from __future__ import annotations

from wc2026.source_loaders import load_sample_teams


def main() -> None:
    teams = load_sample_teams()
    print(f"Loaded {len(teams)} sample team records.")


if __name__ == "__main__":
    main()
