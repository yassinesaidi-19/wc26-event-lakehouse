"""Build dim_team."""

from __future__ import annotations

from wc2026.pipeline import build_dim_team


def main() -> None:
    output_path = build_dim_team()
    print(f"Wrote dim_team to {output_path}")


if __name__ == "__main__":
    main()
