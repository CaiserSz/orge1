"""
ESP32 Status Parser Module
Created: 2025-12-12 10:45:00
Last Modified: 2025-12-12 10:45:00
Version: 1.0.0
Description: ESP32 status mesajlarını analiz ederek olay logları üreten modül
"""

import logging
import time
from typing import Any, Dict, Optional

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.event_detector import ESP32State
from api.logging_config import esp32_logger, log_incident


class StatusInspector:
    """
    Status mesajlarını analiz ederek olay logları üreten sınıf
    """

    def __init__(self):
        """Status inspector başlatıcı"""
        self._warning_throttle: Dict[str, float] = {}
        self._warning_throttle_window = 5.0  # saniye
        self._last_current_draw_ts: Optional[float] = None
        self._zero_current_alerted = False
        self._zero_current_threshold = 120.0  # saniye

    def _throttled_log(
        self,
        key: str,
        message: str,
        level: int = logging.WARNING,
        incident_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Sık tekrarlayan uyarıları throttle ederek logla."""
        now = time.time()
        last = self._warning_throttle.get(key, 0)
        if now - last < self._warning_throttle_window:
            return
        self._warning_throttle[key] = now
        esp32_logger.log(level, message)
        if incident_payload:
            log_incident(
                title=incident_payload.get("title", "ESP32 warning"),
                severity=incident_payload.get("severity", "warning"),
                description=message,
                **{
                    k: v
                    for k, v in incident_payload.items()
                    if k not in {"title", "severity"}
                },
            )

    def inspect_status_for_incidents(self, status: Dict[str, Any]) -> None:
        """
        Status mesajlarını analiz ederek olay logları üret.

        Args:
            status: Status mesajı dict'i
        """
        warning_text = ""
        for key in ("WARNING", "MESSAGE", "MSG"):
            value = status.get(key)
            if isinstance(value, str):
                warning_text = value.lower()
                break

        if warning_text and "external" in warning_text and "power" in warning_text:
            self._throttled_log(
                key="external-equipment-warning",
                message="EV external equipment power uyarısı aldı",
                incident_payload={
                    "title": "EV external equipment warning",
                    "severity": "warning",
                    "status": status,
                },
            )

        state = status.get("STATE")
        current_a = status.get("CABLE") or status.get("CURRENT")
        now = time.time()

        if state == ESP32State.CHARGING.value:
            if current_a and float(current_a) > 0:
                self._last_current_draw_ts = now
                self._zero_current_alerted = False
            else:
                if self._last_current_draw_ts is None:
                    self._last_current_draw_ts = now
                elif (
                    not self._zero_current_alerted
                    and now - self._last_current_draw_ts >= self._zero_current_threshold
                ):
                    self._zero_current_alerted = True
                    self._throttled_log(
                        key="charging-no-current",
                        message=(
                            "EV CHARGING state'te olmasına rağmen akım çekmiyor "
                            f"({self._zero_current_threshold:.0f}s üzeri)"
                        ),
                        incident_payload={
                            "title": "EV charging without current",
                            "severity": "warning",
                            "status": status,
                            "threshold_seconds": self._zero_current_threshold,
                        },
                    )
        else:
            self._last_current_draw_ts = None
            self._zero_current_alerted = False
