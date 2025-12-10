"""
Database Queries Module
Created: 2025-12-10 20:30:00
Last Modified: 2025-12-10 20:30:00
Version: 1.0.0
Description: Database query metodları - Query operations mixin
"""

import sqlite3
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import sys
import os

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from api.logging_config import system_logger

# Model modülünü import et
from api.database import models


class DatabaseQueryMixin:
    """
    Database query metodları mixin
    Bu mixin Database sınıfına query metodlarını ekler
    """

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
        Yeni session oluştur

        Args:
            session_id: Session UUID
            start_time: Başlangıç zamanı
            start_state: Başlangıç state'i
            events: Event listesi
            metadata: Metadata dict'i

        Returns:
            Başarı durumu
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                now_timestamp = int(datetime.now().timestamp())
                start_time_timestamp = int(start_time.timestamp())

                cursor.execute(
                    """
                    INSERT INTO sessions
                    (session_id, user_id, start_time, end_time, start_state, end_state,
                     status, events, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        now_timestamp,
                        now_timestamp,
                    ),
                )

                conn.commit()
                # Cache'i temizle (yeni session eklendi)
                self._clear_cache("sessions:")
                return True
            except sqlite3.IntegrityError:
                # Session zaten var
                system_logger.warning(f"Session already exists: {session_id}")
                return False
            except Exception as e:
                system_logger.error(f"Create session error: {e}", exc_info=True)
                conn.rollback()
                return False

    def update_session(
        self,
        session_id: str,
        end_time: Optional[datetime] = None,
        end_state: Optional[int] = None,
        status: Optional[str] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        # Metrikler
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
        Session güncelle

        Args:
            session_id: Session UUID
            end_time: Bitiş zamanı (opsiyonel)
            end_state: Bitiş state'i (opsiyonel)
            status: Status (opsiyonel)
            events: Event listesi (opsiyonel)
            metadata: Metadata dict'i (opsiyonel)

        Returns:
            Başarı durumu
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Mevcut session'ı al
                cursor.execute(
                    "SELECT events, metadata FROM sessions WHERE session_id = ?",
                    (session_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return False

                # Güncelleme için değerleri hazırla
                update_fields = []
                update_values = []

                if end_time is not None:
                    update_fields.append("end_time = ?")
                    update_values.append(int(end_time.timestamp()))

                if end_state is not None:
                    update_fields.append("end_state = ?")
                    update_values.append(end_state)

                if status is not None:
                    update_fields.append("status = ?")
                    update_values.append(status)

                if events is not None:
                    update_fields.append("events = ?")
                    update_values.append(json.dumps(events))
                elif row["events"]:
                    # Mevcut events'i koru
                    pass

                if metadata is not None:
                    update_fields.append("metadata = ?")
                    update_values.append(json.dumps(metadata))
                elif row["metadata"]:
                    # Mevcut metadata'yı koru
                    pass

                # Metrikleri ekle
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

                for metric_name, metric_value in metrics.items():
                    if metric_value is not None:
                        update_fields.append(f"{metric_name} = ?")
                        update_values.append(metric_value)

                update_fields.append("updated_at = ?")
                update_values.append(int(datetime.now().timestamp()))
                update_values.append(session_id)

                # UPDATE sorgusu
                query = f"UPDATE sessions SET {', '.join(update_fields)} WHERE session_id = ?"
                cursor.execute(query, update_values)

                conn.commit()
                # Cache'i temizle (session güncellendi)
                self._clear_cache("sessions:")
                return True
            except Exception as e:
                system_logger.error(f"Update session error: {e}", exc_info=True)
                conn.rollback()
                return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Belirli bir session'ı al

        Args:
            session_id: Session UUID

        Returns:
            Session dict'i veya None
        """
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
            except Exception as e:
                system_logger.error(f"Get session error: {e}", exc_info=True)
                return None

    def get_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Session listesini al

        Args:
            limit: Maksimum döndürülecek session sayısı
            offset: Başlangıç offset'i
            status: Status filtresi (opsiyonel)
            user_id: User ID filtresi (opsiyonel)
            use_cache: Cache kullan (varsayılan: True)

        Returns:
            Session listesi
        """
        # Cache key oluştur (offset hariç - pagination için cache kullanılmaz)
        cache_key = f"sessions:{status}:{user_id}:{limit}"
        if use_cache and offset == 0:
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result

        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Query builder
                where_clauses = []
                params = []

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

                # Cache'e kaydet (sadece offset=0 için)
                if use_cache and offset == 0:
                    self._set_cache(cache_key, result)

                return result
            except Exception as e:
                system_logger.error(f"Get sessions error: {e}", exc_info=True)
                return []

    def get_session_count(
        self, status: Optional[str] = None, user_id: Optional[str] = None
    ) -> int:
        """
        Session sayısını al

        Args:
            status: Status filtresi (opsiyonel)
            user_id: User ID filtresi (opsiyonel)

        Returns:
            Session sayısı
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Query builder
                where_clauses = []
                params = []

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
            except Exception as e:
                system_logger.error(f"Get session count error: {e}", exc_info=True)
                return 0

    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """
        Aktif session'ı al (status = 'ACTIVE' ve end_time IS NULL)

        Returns:
            Aktif session dict'i veya None
        """
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
            except Exception as e:
                system_logger.error(f"Get current session error: {e}", exc_info=True)
                return None

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
        """
        Yeni event oluştur (normalized)

        Args:
            session_id: Session UUID
            event_type: Event type
            event_timestamp: Event zamanı
            from_state: Önceki state
            to_state: Yeni state
            from_state_name: Önceki state adı
            to_state_name: Yeni state adı
            current_a: Akım (A)
            voltage_v: Voltaj (V)
            power_kw: Güç (kW)
            event_data: Event data dict'i
            status_data: Status data dict'i

        Returns:
            Başarı durumu
        """
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

                # Session event_count'u güncelle
                cursor.execute(
                    """
                    UPDATE sessions
                    SET event_count = event_count + 1, updated_at = ?
                    WHERE session_id = ?
                    """,
                    (created_at_int, session_id),
                )

                conn.commit()
                return True
            except Exception as e:
                system_logger.error(f"Create event error: {e}", exc_info=True)
                conn.rollback()
                return False

    def get_session_events(
        self,
        session_id: str,
        event_type: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Session event'lerini al

        Args:
            session_id: Session UUID
            event_type: Event type filtresi (opsiyonel)
            limit: Maksimum döndürülecek event sayısı
            offset: Başlangıç offset'i

        Returns:
            Event listesi
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Query builder
                where_clauses = ["session_id = ?"]
                params = [session_id]

                if event_type:
                    where_clauses.append("event_type = ?")
                    params.append(event_type)

                if user_id:
                    where_clauses.append("user_id = ?")
                    params.append(user_id)

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
            except Exception as e:
                system_logger.error(f"Get session events error: {e}", exc_info=True)
                return []

    def migrate_events_to_table(self, session_id: Optional[str] = None) -> int:
        """
        Mevcut events JSON'ını session_events tablosuna migrate et

        Args:
            session_id: Belirli bir session (None ise tüm session'lar)

        Returns:
            Migrate edilen event sayısı
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                migrated_count = 0

                # Session'ları al
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

                    # Her event'i session_events tablosuna ekle
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

                        # Event'i kaydet
                        success = self.create_event(
                            session_id=session_id_val,
                            event_type=event_type,
                            event_timestamp=event_timestamp,
                            from_state=event_data.get("from_state"),
                            to_state=event_data.get("to_state"),
                            from_state_name=event_data.get("from_state_name"),
                            to_state_name=event_data.get("to_state_name"),
                            current_a=status.get("CABLE") or status.get("CURRENT"),
                            voltage_v=status.get("CPV") or status.get("PPV"),
                            power_kw=None,  # Hesaplanacak
                            event_data=event_data,
                            status_data=status,
                        )

                        if success:
                            migrated_count += 1

                conn.commit()
                system_logger.info(
                    f"Migrated {migrated_count} events to session_events table"
                )
                return migrated_count
            except Exception as e:
                system_logger.error(f"Migrate events error: {e}", exc_info=True)
                conn.rollback()
                return 0

    def cleanup_old_sessions(self, max_sessions: int = 1000) -> int:
        """
        Eski session'ları temizle

        Args:
            max_sessions: Maksimum saklanacak session sayısı

        Returns:
            Silinen session sayısı
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Toplam session sayısını kontrol et
                cursor.execute("SELECT COUNT(*) FROM sessions")
                total_count = cursor.fetchone()[0]

                if total_count <= max_sessions:
                    return 0

                # Silinecek session sayısı (%10)
                to_remove = int(total_count * 0.1)

                # En eski session'ları sil
                cursor.execute(
                    """
                    DELETE FROM sessions
                    WHERE session_id IN (
                        SELECT session_id FROM sessions
                        ORDER BY start_time ASC
                        LIMIT ?
                    )
                    """,
                    (to_remove,),
                )

                conn.commit()
                deleted_count = cursor.rowcount
                system_logger.info(
                    f"Cleaned up {deleted_count} old sessions (total: {total_count})"
                )
                return deleted_count
            except Exception as e:
                system_logger.error(f"Cleanup old sessions error: {e}", exc_info=True)
                conn.rollback()
                return 0
