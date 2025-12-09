"""
Session Status Enum
Created: 2025-12-10 05:00:00
Last Modified: 2025-12-10 05:00:00
Version: 2.0.0
Description: Session durumları enum
"""

from enum import Enum


class SessionStatus(Enum):
    """Session durumları"""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAULTED = "FAULTED"
