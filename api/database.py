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

                # Sessions tablosu
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        start_state INTEGER NOT NULL,
                        end_state INTEGER,
                        status TEXT NOT NULL,
                        events TEXT NOT NULL,
                        metadata TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

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
                now = datetime.now().isoformat()

                cursor.execute(
                    """
                    INSERT INTO sessions
                    (session_id, start_time, end_time, start_state, end_state,
                     status, events, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        start_time.isoformat(),
                        None,
                        start_state,
                        None,
                        "ACTIVE",
                        json.dumps(events),
                        json.dumps(metadata),
                        now,
                        now,
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
                    update_values.append(end_time.isoformat())

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

                update_fields.append("updated_at = ?")
                update_values.append(datetime.now().isoformat())
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
    ) -> List[Dict[str, Any]]:
        """
        Session listesini al

        Args:
            limit: Maksimum döndürülecek session sayısı
            offset: Başlangıç offset'i
            status: Status filtresi (opsiyonel)

        Returns:
            Session listesi
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                if status:
                    cursor.execute(
                        """
                        SELECT * FROM sessions
                        WHERE status = ?
                        ORDER BY start_time DESC
                        LIMIT ? OFFSET ?
                        """,
                        (status, limit, offset),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT * FROM sessions
                        ORDER BY start_time DESC
                        LIMIT ? OFFSET ?
                        """,
                        (limit, offset),
                    )

                rows = cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]
            except Exception as e:
                system_logger.error(f"Get sessions error: {e}", exc_info=True)
                return []
            finally:
                conn.close()

    def get_session_count(self, status: Optional[str] = None) -> int:
        """
        Session sayısını al

        Args:
            status: Status filtresi (opsiyonel)

        Returns:
            Session sayısı
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                if status:
                    cursor.execute(
                        "SELECT COUNT(*) FROM sessions WHERE status = ?", (status,)
                    )
                else:
                    cursor.execute("SELECT COUNT(*) FROM sessions")

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
        return {
            "session_id": row["session_id"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "start_state": row["start_state"],
            "end_state": row["end_state"],
            "status": row["status"],
            "events": json.loads(row["events"]),
            "metadata": json.loads(row["metadata"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            # Hesaplanan alanlar
            "duration_seconds": (
                (
                    datetime.fromisoformat(row["end_time"])
                    - datetime.fromisoformat(row["start_time"])
                ).total_seconds()
                if row["end_time"]
                else None
            ),
            "event_count": len(json.loads(row["events"])),
        }

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
