"""Shared status normalization helpers."""

from __future__ import annotations


_FINISHED = {"FT", "AET", "PEN", "FINISHED", "MATCH FINISHED", "COMPLETED"}
_SCHEDULED = {"NS", "TIMED", "SCHEDULED", "NOT STARTED"}
_LIVE = {"1H", "2H", "HT", "LIVE", "IN_PLAY", "ET", "BT", "INT"}
_POSTPONED = {"PST", "POSTPONED"}
_CANCELLED = {"CANC", "CANCELLED", "ABD", "ABANDONED", "SUSPENDED"}


def normalize_match_status(*values: object) -> str:
    """Map source-specific status variants into canonical statuses."""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        upper = text.upper()
        if upper in _FINISHED:
            return "FINISHED"
        if upper in _SCHEDULED:
            return "SCHEDULED"
        if upper in _LIVE:
            return "LIVE"
        if upper in _POSTPONED:
            return "POSTPONED"
        if upper in _CANCELLED:
            return "CANCELLED"
    return "UNKNOWN"
