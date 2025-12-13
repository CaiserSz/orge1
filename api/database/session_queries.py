"""
Session Queries Module
Created: 2025-12-10 21:09:49
Last Modified: 2025-12-13 20:47:00
Version: 1.0.1
Description: Session CRUD ve sorgu operasyonları mixin'i.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from api.database import models
from api.logging_config import system_logger


class SessionQueryMixin:
    """Session CRUD ve sorgu operasyonlarını sağlayan mixin."""

    def create_session(
        self,
        session_id: str,
        start_time: datetime,
        start_state: int,
        events: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Yeni session kaydı oluşturur.

        Returns:
            İşlem başarı durumu.
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                now_timestamp = int(datetime.now().timestamp())
                start_time_timestamp = int(start_time.timestamp())
                start_energy_kwh = None
                try:
                    meta_val = metadata.get("start_energy_kwh")
                    if isinstance(meta_val, (int, float)) and meta_val >= 0:
                        start_energy_kwh = float(meta_val)
                except Exception:
                    start_energy_kwh = None

                cursor.execute(
                    """
                    INSERT INTO sessions
                    (session_id, user_id, start_time, end_time, start_state, end_state,
                     status, events, metadata, start_energy_kwh, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        user_id,
                        start_time_timestamp,
                        None,
                        start_state,
                        None,
                        "ACTIVE",
                        json.dumps(events),
                        json.dumps(metadata),
                        start_energy_kwh,
                        now_timestamp,
                        now_timestamp,
                    ),
                )

                conn.commit()
                self._clear_cache("sessions:")
                return True
            except sqlite3.IntegrityError:
                system_logger.warning(f"Session already exists: {session_id}")
                return False
            except Exception as exc:
                system_logger.error(f"Create session error: {exc}", exc_info=True)
                conn.rollback()
                return False

    def cancel_other_active_sessions(
        self,
        exclude_session_id: Optional[str] = None,
        end_time: Optional[datetime] = None,
        end_state: Optional[int] = None,
        status: str = "CANCELLED",
    ) -> int:
        """
        Tek konnektör varsayımıyla, aynı anda birden fazla ACTIVE session kalmasını önlemek için
        ACTIVE & end_time IS NULL kayıtlarını topluca kapatır.

        Returns:
            Güncellenen satır sayısı.
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                now = end_time or datetime.now()
                now_ts = int(now.timestamp())
                end_state_val = int(end_state) if end_state is not None else None
                updated_at = int(datetime.now().timestamp())

                if exclude_session_id:
                    cursor.execute(
                        """
                        UPDATE sessions
                        SET end_time = ?, end_state = ?, status = ?, updated_at = ?
                        WHERE status = 'ACTIVE' AND end_time IS NULL AND session_id != ?
                        """,
                        (now_ts, end_state_val, status, updated_at, exclude_session_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE sessions
                        SET end_time = ?, end_state = ?, status = ?, updated_at = ?
                        WHERE status = 'ACTIVE' AND end_time IS NULL
                        """,
                        (now_ts, end_state_val, status, updated_at),
                    )

                affected = cursor.rowcount or 0
                conn.commit()
                self._clear_cache("sessions:")
                return int(affected)
            except Exception as exc:
                system_logger.error(
                    f"Cancel other active sessions error: {exc}", exc_info=True
                )
                conn.rollback()
                return 0

    def update_session(
        self,
        session_id: str,
        end_time: Optional[datetime] = None,
        end_state: Optional[int] = None,
        status: Optional[str] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_seconds: Optional[int] = None,
        charging_duration_seconds: Optional[int] = None,
        idle_duration_seconds: Optional[int] = None,
        total_energy_kwh: Optional[float] = None,
        start_energy_kwh: Optional[float] = None,
        end_energy_kwh: Optional[float] = None,
        max_power_kw: Optional[float] = None,
        avg_power_kw: Optional[float] = None,
        min_power_kw: Optional[float] = None,
        max_current_a: Optional[float] = None,
        avg_current_a: Optional[float] = None,
        min_current_a: Optional[float] = None,
        set_current_a: Optional[float] = None,
        max_voltage_v: Optional[float] = None,
        avg_voltage_v: Optional[float] = None,
        min_voltage_v: Optional[float] = None,
        event_count: Optional[int] = None,
    ) -> bool:
        """
        Session günceller ve gerekli alanları set eder.

        Returns:
            İşlem başarı durumu.
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                existing_row = self._fetch_existing_session(cursor, session_id)
                if not existing_row:
                    return False

                metrics = {
                    "duration_seconds": duration_seconds,
                    "charging_duration_seconds": charging_duration_seconds,
                    "idle_duration_seconds": idle_duration_seconds,
                    "total_energy_kwh": total_energy_kwh,
                    "start_energy_kwh": start_energy_kwh,
                    "end_energy_kwh": end_energy_kwh,
                    "max_power_kw": max_power_kw,
                    "avg_power_kw": avg_power_kw,
                    "min_power_kw": min_power_kw,
                    "max_current_a": max_current_a,
                    "avg_current_a": avg_current_a,
                    "min_current_a": min_current_a,
                    "set_current_a": set_current_a,
                    "max_voltage_v": max_voltage_v,
                    "avg_voltage_v": avg_voltage_v,
                    "min_voltage_v": min_voltage_v,
                    "event_count": event_count,
                }

                update_fields, update_values = self._build_session_update_parts(
                    end_time=end_time,
                    end_state=end_state,
                    status=status,
                    events=events,
                    metadata=metadata,
                    metrics=metrics,
                )

                if not update_fields:
                    return True

                update_fields.append("updated_at = ?")
                update_values.append(int(datetime.now().timestamp()))
                update_values.append(session_id)

                query = f"UPDATE sessions SET {', '.join(update_fields)} WHERE session_id = ?"
                cursor.execute(query, update_values)

                conn.commit()
                self._clear_cache("sessions:")
                return True
            except Exception as exc:
                system_logger.error(f"Update session error: {exc}", exc_info=True)
                conn.rollback()
                return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Belirli bir session'ı döndürür."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
                )
                row = cursor.fetchone()
                if row:
                    return models.row_to_dict(row)
                return None
            except Exception as exc:
                system_logger.error(f"Get session error: {exc}", exc_info=True)
                return None

    def get_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Session listesini döndürür."""
        cache_key = f"sessions:{status}:{user_id}:{limit}"
        if use_cache and offset == 0:
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result

        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                where_clauses: List[str] = []
                params: List[Any] = []

                if status:
                    where_clauses.append("status = ?")
                    params.append(status)

                if user_id:
                    where_clauses.append("user_id = ?")
                    params.append(user_id)

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                params.extend([limit, offset])

                cursor.execute(
                    f"""
                    SELECT * FROM sessions
                    WHERE {where_sql}
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                    """,
                    params,
                )

                rows = cursor.fetchall()
                result = [models.row_to_dict(row) for row in rows]

                if use_cache and offset == 0:
                    self._set_cache(cache_key, result)

                return result
            except Exception as exc:
                system_logger.error(f"Get sessions error: {exc}", exc_info=True)
                return []

    def get_session_count(
        self, status: Optional[str] = None, user_id: Optional[str] = None
    ) -> int:
        """Session sayısını döndürür."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                where_clauses: List[str] = []
                params: List[Any] = []

                if status:
                    where_clauses.append("status = ?")
                    params.append(status)

                if user_id:
                    where_clauses.append("user_id = ?")
                    params.append(user_id)

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                cursor.execute(
                    f"SELECT COUNT(*) FROM sessions WHERE {where_sql}", params
                )

                return cursor.fetchone()[0]
            except Exception as exc:
                system_logger.error(f"Get session count error: {exc}", exc_info=True)
                return 0

    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Aktif session kaydını döndürür."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM sessions
                    WHERE status = 'ACTIVE' AND end_time IS NULL
                    ORDER BY start_time DESC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                if row:
                    return models.row_to_dict(row)
                return None
            except Exception as exc:
                system_logger.error(f"Get current session error: {exc}", exc_info=True)
                return None

    # Yardımcılar
    def _fetch_existing_session(self, cursor: sqlite3.Cursor, session_id: str):
        cursor.execute(
            "SELECT events, metadata FROM sessions WHERE session_id = ?", (session_id,)
        )
        return cursor.fetchone()

    def _build_session_update_parts(
        self,
        end_time: Optional[datetime],
        end_state: Optional[int],
        status: Optional[str],
        events: Optional[List[Dict[str, Any]]],
        metadata: Optional[Dict[str, Any]],
        metrics: Dict[str, Optional[Any]],
    ) -> Tuple[List[str], List[Any]]:
        update_fields: List[str] = []
        update_values: List[Any] = []

        if end_time is not None:
            update_fields.append("end_time = ?")
            update_values.append(int(end_time.timestamp()))

        if end_state is not None:
            update_fields.append("end_state = ?")
            update_values.append(end_state)

        if status is not None:
            update_fields.append("status = ?")
            update_values.append(status)

        self._append_json_field(update_fields, update_values, "events", events)
        self._append_json_field(update_fields, update_values, "metadata", metadata)
        self._append_metric_updates(update_fields, update_values, metrics)

        return update_fields, update_values

    def _append_json_field(
        self,
        update_fields: List[str],
        update_values: List[Any],
        field_name: str,
        payload: Optional[Any],
    ) -> None:
        if payload is not None:
            update_fields.append(f"{field_name} = ?")
            update_values.append(json.dumps(payload))

    def _append_metric_updates(
        self,
        update_fields: List[str],
        update_values: List[Any],
        metrics: Dict[str, Optional[Any]],
    ) -> None:
        for metric_name, metric_value in metrics.items():
            if metric_value is not None:
                update_fields.append(f"{metric_name} = ?")
                update_values.append(metric_value)
