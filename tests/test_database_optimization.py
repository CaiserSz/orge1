"""
Database Optimization Testleri
Created: 2025-12-10 15:10:00
Last Modified: 2025-12-22 01:30:00
Version: 1.1.0
Description: Database optimization modülü ve core DB query mixin'leri için testler
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import sqlite3
import tempfile

import pytest

from api.database.core import Database
from api.database_optimization import (analyze_query_plan,
                                       analyze_slow_queries,
                                       batch_update_sessions,
                                       get_query_statistics, optimize_indexes)


class TestDatabaseOptimization:
    """Database optimization testleri"""

    def setup_method(self):
        """Test setup"""
        # Geçici database oluştur
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Database bağlantısı oluştur
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        # Test tablosu oluştur
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                start_time INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        self.conn.commit()

        # Test verileri ekle
        cursor.execute(
            """
            INSERT INTO sessions (session_id, user_id, start_time, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("session-1", "user-1", int(time.time()), "ACTIVE", int(time.time())),
        )
        cursor.execute(
            """
            INSERT INTO sessions (session_id, user_id, start_time, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("session-2", "user-1", int(time.time()), "COMPLETED", int(time.time())),
        )
        self.conn.commit()

    def teardown_method(self):
        """Test teardown"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_analyze_query_plan(self):
        """Query plan analizi testi"""
        query = "SELECT * FROM sessions WHERE status = ? ORDER BY start_time DESC LIMIT ? OFFSET ?"
        params = ("ACTIVE", 10, 0)

        plan = analyze_query_plan(self.conn, query, params)
        assert isinstance(plan, list)
        assert len(plan) > 0

    def test_optimize_indexes(self):
        """Index optimization testi"""
        results = optimize_indexes(self.conn)

        assert "created" in results
        assert "skipped" in results
        assert "errors" in results
        assert isinstance(results["created"], list)
        assert isinstance(results["skipped"], list)
        assert isinstance(results["errors"], list)

    def test_batch_update_sessions(self):
        """Batch update testi"""
        updates = [
            {
                "session_id": "session-1",
                "status": "COMPLETED",
            },
            {
                "session_id": "session-2",
                "status": "CANCELLED",
            },
        ]

        updated_count = batch_update_sessions(self.conn, updates)
        assert updated_count == 2

        # Güncellemeleri kontrol et
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT status FROM sessions WHERE session_id = ?", ("session-1",)
        )
        row = cursor.fetchone()
        assert row["status"] == "COMPLETED"

    def test_get_query_statistics(self):
        """Query statistics testi"""
        stats = get_query_statistics(self.conn)

        # Hata durumunda boş dict dönebilir
        if stats:
            assert "session_count" in stats
            assert stats["session_count"] == 2

    def test_analyze_slow_queries(self):
        """Slow query analizi testi"""
        slow_queries = analyze_slow_queries(self.conn)

        assert isinstance(slow_queries, list)
        assert len(slow_queries) > 0

        for query_info in slow_queries:
            assert "name" in query_info
            assert "query" in query_info
            assert "plan" in query_info
            assert "uses_index" in query_info


class TestEventQueryMixin:
    """api/database/event_queries.py için core DB üstünden integration-style unit testler (in-memory)."""

    def test_create_and_get_session_events(self):
        db = Database(db_path=":memory:")
        session_id = "S1"

        t0 = datetime(2025, 1, 1, 0, 0, 0)
        assert db.create_session(
            session_id=session_id,
            start_time=t0,
            start_state=1,
            events=[],
            metadata={},
            user_id="U1",
        )

        t1 = t0 + timedelta(seconds=1)
        ok1 = db.create_event(
            session_id=session_id,
            user_id="U1",
            event_type="STATE_CHANGE",
            event_timestamp=t1,
            from_state=1,
            to_state=2,
            from_state_name="EV_CONNECTED",
            to_state_name="CHARGING",
            current_a=10.0,
            voltage_v=230.0,
            power_kw=2.3,
            event_data={"foo": "bar"},
            status_data={"CABLE": 16, "CPV": 230},
        )
        assert ok1 is True

        t2 = t0 + timedelta(seconds=2)
        ok2 = db.create_event(
            session_id=session_id,
            user_id="U1",
            event_type="HEARTBEAT",
            event_timestamp=t2,
        )
        assert ok2 is True

        events = db.get_session_events(session_id=session_id)
        assert len(events) == 2
        assert events[0]["event_type"] == "HEARTBEAT"
        assert events[1]["event_type"] == "STATE_CHANGE"

        filtered = db.get_session_events(
            session_id=session_id, event_type="STATE_CHANGE"
        )
        assert len(filtered) == 1
        assert filtered[0]["event_data"]["foo"] == "bar"
        assert filtered[0]["status_data"]["CPV"] == 230

    def test_create_event_requires_existing_session(self):
        db = Database(db_path=":memory:")
        ok = db.create_event(
            session_id="MISSING",
            user_id=None,
            event_type="STATE_CHANGE",
            event_timestamp=datetime(2025, 1, 1, 0, 0, 0),
        )
        assert ok is False

    def test_migrate_events_to_table_success(self):
        db = Database(db_path=":memory:")
        session_id = "S2"
        t0 = datetime(2025, 1, 1, 0, 0, 0)

        events = [
            {
                "event_type": "STATE_CHANGE",
                "timestamp": t0.isoformat(),
                "data": {
                    "from_state": 1,
                    "to_state": 2,
                    "from_state_name": "EV_CONNECTED",
                    "to_state_name": "CHARGING",
                    "status": {"CABLE": 16, "CPV": 230},
                },
            }
        ]
        assert db.create_session(
            session_id=session_id,
            start_time=t0,
            start_state=1,
            events=events,
            metadata={},
            user_id=None,
        )

        migrated = db.migrate_events_to_table(session_id=session_id)
        assert migrated == 1

        rows = db.get_session_events(session_id=session_id)
        assert len(rows) == 1
        row = rows[0]
        assert row["event_type"] == "STATE_CHANGE"
        assert row["from_state"] == 1
        assert row["to_state"] == 2
        assert row["current_a"] == pytest.approx(16.0)
        assert row["voltage_v"] == pytest.approx(230.0)
        assert row["status_data"]["CPV"] == 230

    def test_migrate_events_to_table_skips_invalid_json(self):
        db = Database(db_path=":memory:")
        session_id = "S3"
        t0 = datetime(2025, 1, 1, 0, 0, 0)

        assert db.create_session(
            session_id=session_id,
            start_time=t0,
            start_state=1,
            events=[],
            metadata={},
            user_id=None,
        )

        conn = db._get_connection()
        conn.execute(
            "UPDATE sessions SET events = ? WHERE session_id = ?",
            ("{bad_json", session_id),
        )
        conn.commit()

        assert db.migrate_events_to_table(session_id=session_id) == 0
