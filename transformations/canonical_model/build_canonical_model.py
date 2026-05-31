"""Build all canonical model outputs."""

from __future__ import annotations

from wc2026.pipeline import build_canonical_model


def main() -> None:
    output_paths = build_canonical_model()
    for output_path in output_paths:
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
