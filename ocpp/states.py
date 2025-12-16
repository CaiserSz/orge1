"""
OCPP Station State Helpers (Phase-1)

Created: 2025-12-16 01:20
Last Modified: 2025-12-16 01:20
Version: 0.1.0
Description:
  Shared datatypes and helper utilities for the station OCPP client.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StationIdentity:
    """
    Minimal identity fields used in BootNotification and logging.

    Note:
      Phase-1 focuses on single-connector AC station `ORGE_AC_001`.
      These values are not sourced from the FastAPI runtime to keep isolation.
    """

    station_name: str
    vendor_name: str
    model: str
    firmware_version: str


