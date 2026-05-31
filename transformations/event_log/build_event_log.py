"""Build the immutable tournament event log."""

from __future__ import annotations

from wc2026.pipeline import build_event_log


def main() -> None:
    output_path = build_event_log()
    print(f"Wrote event log to {output_path}")


if __name__ == "__main__":
    main()
