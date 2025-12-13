"""
Alerting Data Models
Created: 2025-12-13 02:05:00
Last Modified: 2025-12-13 18:00:00
Version: 1.0.1
Description: AlertSeverity, Alert ve AlertRule tanımları.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Optional

from api.logging_config import system_logger

__all__ = ["AlertSeverity", "Alert", "AlertRule"]


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert:
    """Alert representation"""

    def __init__(
        self,
        name: str,
        severity: AlertSeverity,
        message: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict] = None,
    ):
        self.name = name
        self.severity = severity
        self.message = message
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"Alert(name={self.name}, severity={self.severity.value}, message={self.message})"


class AlertRule:
    """Alert rule definition"""

    def __init__(
        self,
        name: str,
        severity: AlertSeverity,
        check_function: Callable[[], Optional[Alert]],
        enabled: bool = True,
    ):
        self.name = name
        self.severity = severity
        self.check_function = check_function
        self.enabled = enabled

    def evaluate(self, bridge=None, event_detector=None) -> Optional[Alert]:
        """Evaluate alert rule"""
        if not self.enabled:
            return None

        try:
            return self.check_function(bridge=bridge, event_detector=event_detector)
        except Exception as exc:
            system_logger.error(
                f"Alert rule '{self.name}' evaluation error: {exc}", exc_info=True
            )
            return None
