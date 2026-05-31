"""Inspect available Fjelstul dataset files."""

from __future__ import annotations

from wc2026.pipeline import ingest_fjelstul


def main() -> None:
    summary = ingest_fjelstul()
    print(f"Discovered {len(summary['files'])} Fjelstul files.")
    print(
        f"Loaded {summary['teams']} teams, {summary['players']} players, and {summary['matches']} matches."
    )


if __name__ == "__main__":
    main()
