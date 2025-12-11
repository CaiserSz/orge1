"""
Event Queries Module
Created: 2025-12-10 21:09:49
Last Modified: 2025-12-10 21:09:49
Version: 1.0.0
Description: Session event işlemleri ve migration mixin'i.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.database import models
from api.logging_config import system_logger


class EventQueryMixin:
    """Event CRUD ve migration operasyonlarını sağlayan mixin."""

    def create_event(
        self,
        session_id: str,
        event_type: str,
        event_timestamp: datetime,
        from_state: Optional[int] = None,
        to_state: Optional[int] = None,
        from_state_name: Optional[str] = None,
        to_state_name: Optional[str] = None,
        current_a: Optional[float] = None,
        voltage_v: Optional[float] = None,
        power_kw: Optional[float] = None,
        event_data: Optional[Dict[str, Any]] = None,
        status_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """Yeni event kaydı oluşturur (normalized)."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                timestamp_int = int(event_timestamp.timestamp())
                created_at_int = int(datetime.now().timestamp())

                cursor.execute(
                    """
                    INSERT INTO session_events
                    (session_id, user_id, event_type, event_timestamp, from_state, to_state,
                     from_state_name, to_state_name, current_a, voltage_v, power_kw,
                     event_data, status_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        user_id,
                        event_type,
                        timestamp_int,
                        from_state,
                        to_state,
                        from_state_name,
                        to_state_name,
                        current_a,
                        voltage_v,
                        power_kw,
                        json.dumps(event_data) if event_data else None,
                        json.dumps(status_data) if status_data else None,
                        created_at_int,
                    ),
                )

                conn.commit()
                self._clear_cache("sessions:")
                return True
            except Exception as exc:
                system_logger.error(f"Create event error: {exc}", exc_info=True)
                conn.rollback()
                return False

    def get_session_events(
        self,
        session_id: str,
        limit: int = 1000,
        offset: int = 0,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Session'a ait event listesini döndürür."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                where_clauses: List[str] = ["session_id = ?"]
                params: List[Any] = [session_id]

                if event_type:
                    where_clauses.append("event_type = ?")
                    params.append(event_type)

                where_sql = " AND ".join(where_clauses)
                params.extend([limit, offset])

                cursor.execute(
                    f"""
                    SELECT * FROM session_events
                    WHERE {where_sql}
                    ORDER BY event_timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    params,
                )

                rows = cursor.fetchall()
                return [models.event_row_to_dict(row) for row in rows]
            except Exception as exc:
                system_logger.error(f"Get session events error: {exc}", exc_info=True)
                return []

    def migrate_events_to_table(self, session_id: Optional[str] = None) -> int:
        """
        Session kayıtlarındaki events JSON'ını session_events tablosuna taşır.

        Returns:
            Migrate edilen event sayısı.
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                migrated_count = 0

                if session_id:
                    cursor.execute(
                        "SELECT session_id, events FROM sessions WHERE session_id = ?",
                        (session_id,),
                    )
                else:
                    cursor.execute("SELECT session_id, events FROM sessions")

                rows = cursor.fetchall()
                for row in rows:
                    session_id_val = row["session_id"]
                    events_json = row["events"]

                    try:
                        events = json.loads(events_json)
                    except (json.JSONDecodeError, TypeError):
                        continue

                    migrated_count += self._migrate_session_events(
                        session_id_val, events
                    )

                conn.commit()
                system_logger.info(
                    f"Migrated {migrated_count} events to session_events table"
                )
                return migrated_count
            except Exception as exc:
                system_logger.error(f"Migrate events error: {exc}", exc_info=True)
                conn.rollback()
                return 0

    def _migrate_session_events(
        self, session_id: str, events: List[Dict[str, Any]]
    ) -> int:
        migrated_count = 0
        for event in events:
            event_type = event.get("event_type", "UNKNOWN")
            timestamp_str = event.get("timestamp")
            if not timestamp_str:
                continue

            try:
                event_timestamp = datetime.fromisoformat(timestamp_str)
            except (ValueError, TypeError):
                continue

            event_data = event.get("data", {})
            status = event_data.get("status", {})

            success = self.create_event(
                session_id=session_id,
                event_type=event_type,
                event_timestamp=event_timestamp,
                from_state=event_data.get("from_state"),
                to_state=event_data.get("to_state"),
                from_state_name=event_data.get("from_state_name"),
                to_state_name=event_data.get("to_state_name"),
                current_a=status.get("CABLE") or status.get("CURRENT"),
                voltage_v=status.get("CPV") or status.get("PPV"),
                power_kw=None,
                event_data=event_data,
                status_data=status,
            )

            if success:
                migrated_count += 1

        return migrated_count
