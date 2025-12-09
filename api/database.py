"""
Database Module
Created: 2025-12-10 04:30:00
Last Modified: 2025-12-10 04:30:00
Version: 1.0.0
Description: SQLite database yönetimi ve session storage
"""

import sqlite3
import threading
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import sys
import os

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.logging_config import system_logger


class Database:
    """
    SQLite database yönetim sınıfı

    Thread-safe database operations için wrapper.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Database başlatıcı

        Args:
            db_path: Database dosya yolu (None ise varsayılan kullanılır)
        """
        if db_path is None:
            # Varsayılan database yolu: data/sessions.db
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "sessions.db")

        self.db_path = db_path
        self.lock = threading.Lock()
        self._initialize_database()

    def _initialize_database(self):
        """Database'i başlat ve tabloları oluştur"""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Sessions tablosu (güncellenmiş şema: INTEGER timestamps + metrikler)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        start_time INTEGER NOT NULL,
                        end_time INTEGER,
                        start_state INTEGER NOT NULL CHECK(start_state >= 0 AND start_state <= 8),
                        end_state INTEGER CHECK(end_state IS NULL OR (end_state >= 0 AND end_state <= 8)),
                        status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'COMPLETED', 'CANCELLED', 'FAULTED')),

                        -- Süre metrikleri
                        duration_seconds INTEGER CHECK(duration_seconds IS NULL OR duration_seconds >= 0),
                        charging_duration_seconds INTEGER CHECK(charging_duration_seconds IS NULL OR charging_duration_seconds >= 0),
                        idle_duration_seconds INTEGER CHECK(idle_duration_seconds IS NULL OR idle_duration_seconds >= 0),

                        -- Enerji metrikleri
                        total_energy_kwh REAL CHECK(total_energy_kwh IS NULL OR total_energy_kwh >= 0),
                        start_energy_kwh REAL CHECK(start_energy_kwh IS NULL OR start_energy_kwh >= 0),
                        end_energy_kwh REAL CHECK(end_energy_kwh IS NULL OR end_energy_kwh >= 0),

                        -- Güç metrikleri
                        max_power_kw REAL CHECK(max_power_kw IS NULL OR max_power_kw >= 0),
                        avg_power_kw REAL CHECK(avg_power_kw IS NULL OR avg_power_kw >= 0),
                        min_power_kw REAL CHECK(min_power_kw IS NULL OR min_power_kw >= 0),

                        -- Akım metrikleri
                        max_current_a REAL CHECK(max_current_a IS NULL OR max_current_a >= 0),
                        avg_current_a REAL CHECK(avg_current_a IS NULL OR avg_current_a >= 0),
                        min_current_a REAL CHECK(min_current_a IS NULL OR min_current_a >= 0),
                        set_current_a REAL CHECK(set_current_a IS NULL OR set_current_a >= 0),

                        -- Voltaj metrikleri
                        max_voltage_v REAL CHECK(max_voltage_v IS NULL OR max_voltage_v >= 0),
                        avg_voltage_v REAL CHECK(avg_voltage_v IS NULL OR avg_voltage_v >= 0),
                        min_voltage_v REAL CHECK(min_voltage_v IS NULL OR min_voltage_v >= 0),

                        -- Event ve metadata
                        event_count INTEGER DEFAULT 0 CHECK(event_count >= 0),
                        events TEXT NOT NULL DEFAULT '[]',
                        metadata TEXT NOT NULL DEFAULT '{}',

                        -- Audit fields (INTEGER timestamps)
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                    """
                )

                # Migration: Eski TEXT timestamp kolonları varsa migrate et
                self._migrate_timestamp_columns(cursor)

                # Migration: Yeni metrik kolonlarını ekle (eğer yoksa)
                self._migrate_metrics_columns(cursor)

                # Migration: user_id kolonunu ekle (eğer yoksa)
                self._migrate_user_id_column(cursor)

                # Session events tablosu (normalized)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        user_id TEXT,
                        event_type TEXT NOT NULL,
                        event_timestamp INTEGER NOT NULL,
                        from_state INTEGER,
                        to_state INTEGER,
                        from_state_name TEXT,
                        to_state_name TEXT,
                        current_a REAL,
                        voltage_v REAL,
                        power_kw REAL,
                        event_data TEXT,
                        status_data TEXT,
                        created_at INTEGER NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                    )
                    """
                )

                # Session events index'ler
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_session_events_session_id
                    ON session_events(session_id)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_session_events_event_type
                    ON session_events(event_type)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_session_events_timestamp
                    ON session_events(event_timestamp DESC)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_session_events_session_timestamp
                    ON session_events(session_id, event_timestamp DESC)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_session_events_session_type
                    ON session_events(session_id, event_type)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                    ON sessions(user_id)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sessions_user_start_time
                    ON sessions(user_id, start_time DESC)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_session_events_user_id
                    ON session_events(user_id)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_session_events_user_timestamp
                    ON session_events(user_id, event_timestamp DESC)
                    """
                )

                # Foreign keys aktif et
                cursor.execute("PRAGMA foreign_keys=ON")

                # Index'ler (performans için)
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sessions_start_time
                    ON sessions(start_time DESC)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sessions_status
                    ON sessions(status)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sessions_end_time
                    ON sessions(end_time DESC)
                    """
                )
                # Composite index'ler (performans iyileştirmesi)
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sessions_status_start_time
                    ON sessions(status, start_time DESC)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sessions_status_end_time
                    ON sessions(status, end_time DESC)
                    """
                )

                conn.commit()
                system_logger.info(f"Database initialized: {self.db_path}")
            except Exception as e:
                system_logger.error(
                    f"Database initialization error: {e}", exc_info=True
                )
                conn.rollback()
                raise
            finally:
                conn.close()

    def _migrate_timestamp_columns(self, cursor):
        """
        Eski TEXT timestamp kolonlarını INTEGER'a migrate et

        Args:
            cursor: Database cursor
        """
        try:
            # Mevcut kolonları kontrol et
            cursor.execute("PRAGMA table_info(sessions)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            # Eğer start_time TEXT ise, INTEGER'a çevir
            if columns.get("start_time") == "TEXT":
                system_logger.info(
                    "Migrating timestamp columns from TEXT to INTEGER..."
                )

                # Yeni tablo oluştur
                cursor.execute(
                    """
                    CREATE TABLE sessions_new (
                        session_id TEXT PRIMARY KEY,
                        start_time INTEGER NOT NULL,
                        end_time INTEGER,
                        start_state INTEGER NOT NULL,
                        end_state INTEGER,
                        status TEXT NOT NULL,
                        events TEXT NOT NULL,
                        metadata TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                    """
                )

                # Mevcut verileri migrate et
                cursor.execute("SELECT * FROM sessions")
                rows = cursor.fetchall()

                for row in rows:
                    # TEXT timestamp'leri INTEGER'a çevir
                    start_time_int = int(
                        datetime.fromisoformat(row["start_time"]).timestamp()
                    )
                    end_time_int = (
                        int(datetime.fromisoformat(row["end_time"]).timestamp())
                        if row["end_time"]
                        else None
                    )
                    created_at_int = int(
                        datetime.fromisoformat(row["created_at"]).timestamp()
                    )
                    updated_at_int = int(
                        datetime.fromisoformat(row["updated_at"]).timestamp()
                    )

                    cursor.execute(
                        """
                        INSERT INTO sessions_new
                        (session_id, start_time, end_time, start_state, end_state,
                         status, events, metadata, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["session_id"],
                            start_time_int,
                            end_time_int,
                            row["start_state"],
                            row["end_state"],
                            row["status"],
                            row["events"],
                            row["metadata"],
                            created_at_int,
                            updated_at_int,
                        ),
                    )

                # Eski tabloyu sil ve yenisini yeniden adlandır
                cursor.execute("DROP TABLE sessions")
                cursor.execute("ALTER TABLE sessions_new RENAME TO sessions")

                system_logger.info("Timestamp migration completed successfully")
        except Exception as e:
            # Migration hatası kritik değil (yeni database için)
            system_logger.debug(
                f"Timestamp migration skipped (new database or already migrated): {e}"
            )

    def _migrate_user_id_column(self, cursor):
        """
        user_id kolonunu ekle (eğer yoksa)

        Args:
            cursor: SQLite cursor
        """
        try:
            # sessions tablosuna user_id ekle
            cursor.execute("PRAGMA table_info(sessions)")
            columns = [col[1] for col in cursor.fetchall()]
            if "user_id" not in columns:
                cursor.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
                system_logger.info("user_id kolonu sessions tablosuna eklendi")

            # session_events tablosuna user_id ekle
            cursor.execute("PRAGMA table_info(session_events)")
            columns = [col[1] for col in cursor.fetchall()]
            if "user_id" not in columns:
                cursor.execute("ALTER TABLE session_events ADD COLUMN user_id TEXT")
                system_logger.info("user_id kolonu session_events tablosuna eklendi")
        except Exception as e:
            system_logger.warning(f"user_id migration hatası: {e}")

    def _migrate_metrics_columns(self, cursor):
        """
        Yeni metrik kolonlarını ekle (eğer yoksa)

        Args:
            cursor: Database cursor
        """
        try:
            # Mevcut kolonları kontrol et
            cursor.execute("PRAGMA table_info(sessions)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            # Eklenecek metrik kolonları
            metrics_columns = [
                ("duration_seconds", "INTEGER"),
                ("charging_duration_seconds", "INTEGER"),
                ("idle_duration_seconds", "INTEGER"),
                ("total_energy_kwh", "REAL"),
                ("start_energy_kwh", "REAL"),
                ("end_energy_kwh", "REAL"),
                ("max_power_kw", "REAL"),
                ("avg_power_kw", "REAL"),
                ("min_power_kw", "REAL"),
                ("max_current_a", "REAL"),
                ("avg_current_a", "REAL"),
                ("min_current_a", "REAL"),
                ("set_current_a", "REAL"),
                ("max_voltage_v", "REAL"),
                ("avg_voltage_v", "REAL"),
                ("min_voltage_v", "REAL"),
                ("event_count", "INTEGER DEFAULT 0"),
            ]

            # Eksik kolonları ekle
            for col_name, col_type in metrics_columns:
                if col_name not in existing_columns:
                    try:
                        cursor.execute(
                            f"ALTER TABLE sessions ADD COLUMN {col_name} {col_type}"
                        )
                        system_logger.debug(f"Added column: {col_name}")
                    except sqlite3.OperationalError as e:
                        # Kolon zaten var veya başka bir hata
                        system_logger.debug(
                            f"Column {col_name} already exists or error: {e}"
                        )
        except Exception as e:
            system_logger.warning(f"Metrics columns migration error: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Database connection al

        Returns:
            SQLite connection
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Dict-like row access
        return conn

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
                return True
            except sqlite3.IntegrityError:
                # Session zaten var
                system_logger.warning(f"Session already exists: {session_id}")
                return False
            except Exception as e:
                system_logger.error(f"Create session error: {e}", exc_info=True)
                conn.rollback()
                return False
            finally:
                conn.close()

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
                return True
            except Exception as e:
                system_logger.error(f"Update session error: {e}", exc_info=True)
                conn.rollback()
                return False
            finally:
                conn.close()

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
                    return self._row_to_dict(row)
                return None
            except Exception as e:
                system_logger.error(f"Get session error: {e}", exc_info=True)
                return None
            finally:
                conn.close()

    def get_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Session listesini al

        Args:
            limit: Maksimum döndürülecek session sayısı
            offset: Başlangıç offset'i
            status: Status filtresi (opsiyonel)
            user_id: User ID filtresi (opsiyonel)

        Returns:
            Session listesi
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
                return [self._row_to_dict(row) for row in rows]
            except Exception as e:
                system_logger.error(f"Get sessions error: {e}", exc_info=True)
                return []
            finally:
                conn.close()

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
            finally:
                conn.close()

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
                    return self._row_to_dict(row)
                return None
            except Exception as e:
                system_logger.error(f"Get current session error: {e}", exc_info=True)
                return None
            finally:
                conn.close()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Database row'unu dict'e dönüştür

        Args:
            row: SQLite row

        Returns:
            Session dict'i
        """
        # Timestamp'leri datetime'a çevir (INTEGER → datetime)
        start_time_dt = datetime.fromtimestamp(row["start_time"])
        end_time_dt = (
            datetime.fromtimestamp(row["end_time"]) if row["end_time"] else None
        )
        created_at_dt = datetime.fromtimestamp(row["created_at"])
        updated_at_dt = datetime.fromtimestamp(row["updated_at"])

        result = {
            "session_id": row["session_id"],
            "start_time": start_time_dt.isoformat(),
            "end_time": end_time_dt.isoformat() if end_time_dt else None,
            "start_state": row["start_state"],
            "end_state": row["end_state"],
            "status": row["status"],
            "events": json.loads(row["events"]),
            "metadata": json.loads(row["metadata"]),
            "created_at": created_at_dt.isoformat(),
            "updated_at": updated_at_dt.isoformat(),
            # Hesaplanan alanlar
            "duration_seconds": (
                (end_time_dt - start_time_dt).total_seconds() if end_time_dt else None
            ),
            "event_count": len(json.loads(row["events"])),
        }

        # Metrikleri ekle (eğer varsa)
        metric_fields = [
            "duration_seconds",
            "charging_duration_seconds",
            "idle_duration_seconds",
            "total_energy_kwh",
            "start_energy_kwh",
            "end_energy_kwh",
            "max_power_kw",
            "avg_power_kw",
            "min_power_kw",
            "max_current_a",
            "avg_current_a",
            "min_current_a",
            "set_current_a",
            "max_voltage_v",
            "avg_voltage_v",
            "min_voltage_v",
            "event_count",
        ]

        for field in metric_fields:
            if field in row.keys() and row[field] is not None:
                result[field] = row[field]

        return result

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
            finally:
                conn.close()

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
                return [self._event_row_to_dict(row) for row in rows]
            except Exception as e:
                system_logger.error(f"Get session events error: {e}", exc_info=True)
                return []
            finally:
                conn.close()

    def _event_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Event row'unu dict'e dönüştür

        Args:
            row: SQLite row

        Returns:
            Event dict'i
        """
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "user_id": row.get("user_id"),
            "event_type": row["event_type"],
            "event_timestamp": datetime.fromtimestamp(
                row["event_timestamp"]
            ).isoformat(),
            "from_state": row["from_state"],
            "to_state": row["to_state"],
            "from_state_name": row["from_state_name"],
            "to_state_name": row["to_state_name"],
            "current_a": row["current_a"],
            "voltage_v": row["voltage_v"],
            "power_kw": row["power_kw"],
            "event_data": json.loads(row["event_data"]) if row["event_data"] else None,
            "status_data": (
                json.loads(row["status_data"]) if row["status_data"] else None
            ),
            "created_at": datetime.fromtimestamp(row["created_at"]).isoformat(),
        }

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
            finally:
                conn.close()

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
            finally:
                conn.close()


# Singleton instance
database_instance: Optional[Database] = None
database_lock = threading.Lock()


def get_database(db_path: Optional[str] = None) -> Database:
    """
    Database singleton instance'ı döndür

    Args:
        db_path: Database dosya yolu (opsiyonel)

    Returns:
        Database instance
    """
    global database_instance

    if database_instance is None:
        with database_lock:
            if database_instance is None:
                database_instance = Database(db_path)

    return database_instance
