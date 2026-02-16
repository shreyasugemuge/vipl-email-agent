"""
Shared utilities for the VIPL Email Agent.
"""

import logging
from datetime import datetime
from typing import Optional

import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

# Timestamp format used in the Google Sheet (written by sheet_logger)
SHEET_DATETIME_FORMAT = "%d %b %Y, %I:%M %p"


def parse_sheet_datetime(dt_str: str) -> Optional[datetime]:
    """Parse a datetime string from the Google Sheet into a tz-aware IST datetime.

    Handles:
      - "13 Feb 2026, 02:30 PM"
      - "13 Feb 2026, 02:30 PM IST"
      - "2026-02-13 14:30:00"
    """
    if not dt_str:
        return None
    clean = dt_str.strip()
    for suffix in (" IST", " ist"):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)]
    try:
        dt = datetime.strptime(clean.strip(), SHEET_DATETIME_FORMAT)
        return IST.localize(dt)
    except ValueError:
        try:
            dt = datetime.strptime(clean.strip(), "%Y-%m-%d %H:%M:%S")
            return IST.localize(dt)
        except ValueError:
            return None
