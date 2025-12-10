"""
Database Core Module
Created: 2025-12-10 19:00:00
Last Modified: 2025-12-10 19:00:00
Version: 2.0.0
Description: SQLite database yönetimi ve session storage - Core module
"""

import sqlite3
import threading
import time
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import sys
import os

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from api.logging_config import system_logger

# Migration ve model modüllerini import et
from api.database import migrations
from api.database.queries import DatabaseQueryMixin


class Database(DatabaseQueryMixin):
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
        self._connection: Optional[sqlite3.Connection] = None
        self._connection_lock = threading.Lock()
        # Query result cache (basit in-memory cache)
        self._query_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_ttl = 60.0  # 60 saniye cache TTL
        self._initialize_database()
        # Database optimization'ı başlat
        self._optimize_database()

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
                migrations.migrate_timestamp_columns(cursor)

                # Migration: Yeni metrik kolonlarını ekle (eğer yoksa)
                migrations.migrate_metrics_columns(cursor)

                # Migration: user_id kolonunu ekle (eğer yoksa)
                migrations.migrate_user_id_column(cursor)

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
                # Database optimization index'leri
                self._create_optimization_indexes(cursor)
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
            # Connection persistent - close gerekmez

    def _create_optimization_indexes(self, cursor):
        """
        Database optimization için ek index'ler oluştur

        Args:
            cursor: Database cursor
        """
        try:
            # get_current_session için optimize edilmiş index
            # (status, end_time, start_time) composite index
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_status_end_start
                ON sessions(status, end_time, start_time DESC)
                WHERE end_time IS NULL
                """
            )
            # user_id ve status kombinasyonu için index
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_user_status_start
                ON sessions(user_id, status, start_time DESC)
                """
            )
            system_logger.debug("Optimization indexes created")
        except Exception as e:
            system_logger.warning(f"Optimization index creation failed: {e}")

    def _optimize_database(self):
        """
        Database'i optimize et (index'ler, query plan analizi)
        """
        try:
            from api.database_optimization import optimize_indexes, get_query_statistics

            conn = self._get_connection()
            # Index optimization
            opt_results = optimize_indexes(conn)
            if opt_results.get("created"):
                system_logger.info(
                    f"Database optimization: {len(opt_results['created'])} index created"
                )
            # Query statistics
            stats = get_query_statistics(conn)
            if stats:
                system_logger.debug(f"Database statistics: {stats}")
        except Exception as e:
            system_logger.warning(f"Database optimization failed: {e}")

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """
        Cache'den değer al

        Args:
            key: Cache key

        Returns:
            Cached değer veya None
        """
        if key not in self._query_cache:
            return None

        cached_value, expires_at = self._query_cache[key]
        if time.time() > expires_at:
            del self._query_cache[key]
            return None

        return cached_value

    def _set_cache(self, key: str, value: Any) -> None:
        """
        Cache'e değer kaydet

        Args:
            key: Cache key
            value: Cache edilecek değer
        """
        expires_at = time.time() + self._cache_ttl
        self._query_cache[key] = (value, expires_at)

    def _clear_cache(self, pattern: Optional[str] = None) -> None:
        """
        Cache'i temizle

        Args:
            pattern: Cache key pattern (None ise tüm cache temizlenir)
        """
        if pattern is None:
            self._query_cache.clear()
        else:
            keys_to_delete = [key for key in self._query_cache.keys() if pattern in key]
            for key in keys_to_delete:
                del self._query_cache[key]

    def _get_connection(self) -> sqlite3.Connection:
        """
        Database connection al (persistent connection)

        Returns:
            SQLite connection
        """
        with self._connection_lock:
            if self._connection is None:
                self._connection = sqlite3.connect(
                    self.db_path, check_same_thread=False
                )
                self._connection.row_factory = sqlite3.Row  # Dict-like row access

                # WAL mode aktif et (Write-Ahead Logging - daha iyi concurrency)
                try:
                    self._connection.execute("PRAGMA journal_mode=WAL")
                    system_logger.debug("WAL mode activated")
                except Exception as e:
                    system_logger.warning(f"WAL mode activation failed: {e}")

                # Cache size optimize et (10MB cache)
                try:
                    self._connection.execute(
                        "PRAGMA cache_size=-10000"
                    )  # -10000 = ~10MB
                    system_logger.debug("Cache size optimized")
                except Exception as e:
                    system_logger.warning(f"Cache size optimization failed: {e}")

                # Foreign keys aktif et
                try:
                    self._connection.execute("PRAGMA foreign_keys=ON")
                    system_logger.debug("Foreign keys enabled")
                except Exception as e:
                    system_logger.warning(f"Foreign keys activation failed: {e}")

                # Synchronous mode optimize et (NORMAL - güvenlik ve performans dengesi)
                try:
                    self._connection.execute("PRAGMA synchronous=NORMAL")
                    system_logger.debug("Synchronous mode set to NORMAL")
                except Exception as e:
                    system_logger.warning(f"Synchronous mode optimization failed: {e}")

            return self._connection

    def _close_connection(self):
        """
        Database connection'ı kapat
        """
        with self._connection_lock:
            if self._connection:
                try:
                    self._connection.close()
                except Exception:
                    pass
                    # Connection persistent - close gerekmez
                    self._connection = None


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
