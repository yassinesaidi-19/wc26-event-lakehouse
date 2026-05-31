"""Calculate a simple qualification status view."""

from __future__ import annotations

from wc2026.io_utils import write_csv
from wc2026.paths import STATE_DIR
from wc2026.pipeline import calculate_qualification_status


def main() -> None:
    frame = calculate_qualification_status()
    output_path = STATE_DIR / "state_qualification_status.csv"
    write_csv(output_path, frame)
    print(f"Wrote qualification status to {output_path}")


if __name__ == "__main__":
    main()
