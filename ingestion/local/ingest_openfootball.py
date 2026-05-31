"""Inspect available openfootball dataset files."""

from __future__ import annotations

from wc2026.pipeline import ingest_openfootball


def main() -> None:
    summary = ingest_openfootball()
    print(f"Discovered {len(summary['files'])} openfootball files.")
    print(f"Loaded {summary['teams']} teams and {summary['matches']} matches.")


if __name__ == "__main__":
    main()
