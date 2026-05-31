"""Build fact_match."""

from __future__ import annotations

from wc2026.pipeline import build_fact_match


def main() -> None:
    output_path = build_fact_match()
    print(f"Wrote fact_match to {output_path}")


if __name__ == "__main__":
    main()
