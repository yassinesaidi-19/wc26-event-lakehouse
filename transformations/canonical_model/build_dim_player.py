"""Build dim_player."""

from __future__ import annotations

from wc2026.pipeline import build_dim_player


def main() -> None:
    output_path = build_dim_player()
    print(f"Wrote dim_player to {output_path}")


if __name__ == "__main__":
    main()
