"""Build state_group_standings."""

from __future__ import annotations

from wc2026.pipeline import calculate_group_standings


def main() -> None:
    output_path = calculate_group_standings()
    print(f"Wrote group standings to {output_path}")


if __name__ == "__main__":
    main()
