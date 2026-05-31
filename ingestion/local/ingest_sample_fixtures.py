"""Inspect sample fixture source records."""

from __future__ import annotations

from wc2026.source_loaders import load_sample_fixtures


def main() -> None:
    fixtures = load_sample_fixtures()
    print(f"Loaded {len(fixtures)} sample fixture records.")


if __name__ == "__main__":
    main()
