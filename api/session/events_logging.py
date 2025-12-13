"""
Session Event Logging Helpers
Created: 2025-12-13 02:10:00
Last Modified: 2025-12-13 02:10:00
Version: 1.0.0
Description: Session event loglama ve persistence mixin'i.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from api.event_detector import EventType
from api.logging_config import log_incident, log_session_snapshot, system_logger
from api.session.metrics import calculate_power


class SessionEventLoggingMixin:
    """Session event loglama ve veritabanı yardımcıları."""

    def _log_session_snapshot(
        self,
        session_id: str,
        event_label: str,
        summary: str,
        event_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        snapshot = dict(kwargs)
        if event_data:
            snapshot.update(
                {
                    "from_state": event_data.get("from_state"),
                    "to_state": event_data.get("to_state"),
                    "user_id": event_data.get("user_id")
                    or event_data.get("data", {}).get("user_id"),
                }
            )
            status_payload = (
                event_data.get("status")
                or event_data.get("data", {}).get("status")
                or {}
            )
            if status_payload:
                snapshot["status"] = status_payload
            if "data" in event_data:
                snapshot["raw_data"] = event_data.get("data")

        log_session_snapshot(
            session_id=session_id,
            event_type=event_label,
            summary=summary,
            **snapshot,
        )

    def _save_event_to_table(
        self,
        event_type: EventType,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ):
        if not self.current_session:
            return

        try:
            status = event_data.get("status", {})
            current_a = status.get("CABLE") or status.get("CURRENT")
            voltage_v = status.get("CPV") or status.get("PPV")
            power_kw = None
            if current_a is not None and voltage_v is not None:
                power_kw = calculate_power(current_a, voltage_v)

            if not user_id:
                user_id = self.current_session.metadata.get("user_id")

            self.db.create_event(
                session_id=self.current_session.session_id,
                event_type=event_type.value,
                event_timestamp=datetime.now(),
                from_state=event_data.get("from_state"),
                to_state=event_data.get("to_state"),
                from_state_name=event_data.get("from_state_name"),
                to_state_name=event_data.get("to_state_name"),
                current_a=current_a,
                voltage_v=voltage_v,
                power_kw=power_kw,
                event_data=event_data,
                status_data=status,
                user_id=user_id,
            )
        except Exception as exc:
            system_logger.warning(f"Event kaydetme hatası (session_events): {exc}")
            log_incident(
                title="Session event persistence failed",
                severity="error",
                description=str(exc),
                session_id=(
                    self.current_session.session_id if self.current_session else None
                ),
                event_type=event_type.value,
            )
            if self.current_session:
                self._log_session_snapshot(
                    session_id=self.current_session.session_id,
                    event_label="SESSION_EVENT_PERSISTENCE_ERROR",
                    summary="Session event DB kaydı başarısız",
                    event_data=event_data,
                    error=str(exc),
                )
