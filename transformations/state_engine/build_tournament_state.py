"""Build tournament state outputs."""

from __future__ import annotations

from wc2026.pipeline import build_tournament_state


def main() -> None:
    output_paths = build_tournament_state()
    for output_path in output_paths:
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
