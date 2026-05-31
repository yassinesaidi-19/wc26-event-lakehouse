"""Build fact_match_event."""

from __future__ import annotations

from wc2026.pipeline import build_fact_match_event


def main() -> None:
    output_path = build_fact_match_event()
    print(f"Wrote fact_match_event to {output_path}")


if __name__ == "__main__":
    main()
