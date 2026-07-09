"""Helper functions for API clients.

Provides reusable utilities like date parsing.
"""

from __future__ import annotations

from datetime import date


def parse_date(date_str: str | None) -> date | None:
    """Parse an ISO-format date string.

    Args:
        date_str: Date string in ISO format (YYYY-MM-DD) or None.

    Returns:
        Parsed date object, or None if the string is empty/invalid.
    """
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None
