"""Inspect sample match event source records."""

from __future__ import annotations

from wc2026.source_loaders import load_sample_match_events


def main() -> None:
    events = load_sample_match_events()
    print(f"Loaded {len(events)} sample match event records.")


if __name__ == "__main__":
    main()
