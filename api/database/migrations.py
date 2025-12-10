"""
Database Migrations Module
Created: 2025-12-10 19:00:00
Last Modified: 2025-12-10 19:00:00
Version: 1.0.0
Description: Database migration operations
"""

import sqlite3
from datetime import datetime
import sys
import os

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from api.logging_config import system_logger


def migrate_timestamp_columns(cursor):
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
            system_logger.info("Migrating timestamp columns from TEXT to INTEGER...")

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


def migrate_user_id_column(cursor):
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


def migrate_metrics_columns(cursor):
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
