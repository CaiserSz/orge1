"""
Database Schema Mixin
Created: 2025-12-13 02:20:00
Last Modified: 2025-12-13 02:20:00
Version: 1.0.0
Description: Database şema oluşturma ve optimizasyon yardımcı mixin'i.
"""

from __future__ import annotations

from typing import Any

from api.database import migrations
from api.database_optimization import get_query_statistics, optimize_indexes
from api.logging_config import system_logger


class DatabaseSchemaMixin:
    """Şema oluşturma ve optimizasyon metotlarını sağlayan mixin."""

    def _initialize_database(self):
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

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
                        duration_seconds INTEGER CHECK(duration_seconds IS NULL OR duration_seconds >= 0),
                        charging_duration_seconds INTEGER CHECK(charging_duration_seconds IS NULL OR charging_duration_seconds >= 0),
                        idle_duration_seconds INTEGER CHECK(idle_duration_seconds IS NULL OR idle_duration_seconds >= 0),
                        total_energy_kwh REAL CHECK(total_energy_kwh IS NULL OR total_energy_kwh >= 0),
                        start_energy_kwh REAL CHECK(start_energy_kwh IS NULL OR start_energy_kwh >= 0),
                        end_energy_kwh REAL CHECK(end_energy_kwh IS NULL OR end_energy_kwh >= 0),
                        max_power_kw REAL CHECK(max_power_kw IS NULL OR max_power_kw >= 0),
                        avg_power_kw REAL CHECK(avg_power_kw IS NULL OR avg_power_kw >= 0),
                        min_power_kw REAL CHECK(min_power_kw IS NULL OR min_power_kw >= 0),
                        max_current_a REAL CHECK(max_current_a IS NULL OR max_current_a >= 0),
                        avg_current_a REAL CHECK(avg_current_a IS NULL OR avg_current_a >= 0),
                        min_current_a REAL CHECK(min_current_a IS NULL OR min_current_a >= 0),
                        set_current_a REAL CHECK(set_current_a IS NULL OR set_current_a >= 0),
                        max_voltage_v REAL CHECK(max_voltage_v IS NULL OR max_voltage_v >= 0),
                        avg_voltage_v REAL CHECK(avg_voltage_v IS NULL OR avg_voltage_v >= 0),
                        min_voltage_v REAL CHECK(min_voltage_v IS NULL OR min_voltage_v >= 0),
                        event_count INTEGER DEFAULT 0 CHECK(event_count >= 0),
                        events TEXT NOT NULL DEFAULT '[]',
                        metadata TEXT NOT NULL DEFAULT '{}',
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                    """
                )

                migrations.migrate_timestamp_columns(cursor)
                migrations.migrate_metrics_columns(cursor)
                migrations.migrate_user_id_column(cursor)

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

                cursor.execute("PRAGMA foreign_keys=ON")

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
            except Exception as exc:
                system_logger.error(
                    f"Database initialization error: {exc}", exc_info=True
                )
                conn.rollback()
                raise

    def _create_optimization_indexes(self, cursor: Any):
        try:
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_status_end_start
                ON sessions(status, end_time, start_time DESC)
                WHERE end_time IS NULL
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_user_status_start
                ON sessions(user_id, status, start_time DESC)
                """
            )
            system_logger.debug("Optimization indexes created")
        except Exception as exc:
            system_logger.warning(f"Optimization index creation failed: {exc}")

    def _optimize_database(self):
        try:
            conn = self._get_connection()
            opt_results = optimize_indexes(conn)
            if opt_results.get("created"):
                system_logger.info(
                    f"Database optimization: {len(opt_results['created'])} index created"
                )
            stats = get_query_statistics(conn)
            if stats:
                system_logger.debug(f"Database statistics: {stats}")
        except Exception as exc:
            system_logger.warning(f"Database optimization failed: {exc}")
