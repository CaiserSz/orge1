"""
Database Core Module
Created: 2025-12-10 19:00:00
Last Modified: 2025-12-22 04:17:24
Version: 2.0.1
Description: SQLite database yönetimi ve session storage - Core module
"""

import os
import sqlite3
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from api.database.queries import DatabaseQueryMixin
from api.database.schema_mixin import DatabaseSchemaMixin
from api.logging_config import system_logger


class Database(DatabaseSchemaMixin, DatabaseQueryMixin):
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
        # NOTE: Query mixin'leri iç içe birbirini çağırabiliyor (örn. migrate -> create_event)
        # Bu nedenle reentrant lock kullanıyoruz; aksi halde aynı thread içinde deadlock oluşur.
        self.lock = threading.RLock()
        self._connection: Optional[sqlite3.Connection] = None
        self._connection_lock = threading.Lock()
        # Query result cache (basit in-memory cache)
        self._query_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_ttl = 60.0
        self._initialize_database()
        # Database optimization'ı başlat
        self._optimize_database()

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
