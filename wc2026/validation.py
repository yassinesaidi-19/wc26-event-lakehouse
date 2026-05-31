"""Validation helpers shared across pipeline stages."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def validate_required_fields(
    records: list[dict[str, Any]],
    required_fields: Iterable[str],
    source_name: str,
) -> list[str]:
    """Return validation errors for required field checks."""
    errors: list[str] = []
    for index, record in enumerate(records):
        for field_name in required_fields:
            value = record.get(field_name)
            if value is None or value == "":
                errors.append(
                    f"{source_name} record at index {index} is missing required field '{field_name}'"
                )
    return errors


def validate_unique_field(
    records: list[dict[str, Any]],
    field_name: str,
    source_name: str,
) -> list[str]:
    """Return validation errors for duplicate business keys."""
    seen: set[Any] = set()
    errors: list[str] = []
    for record in records:
        value = record.get(field_name)
        if value in seen:
            errors.append(f"{source_name} contains duplicate {field_name}: {value}")
        seen.add(value)
    return errors


def raise_for_errors(errors: list[str]) -> None:
    """Raise a single ValueError when validation fails."""
    if errors:
        raise ValueError("\n".join(errors))
