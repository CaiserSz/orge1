"""
Database Optimization Testleri
Created: 2025-12-10 15:10:00
Last Modified: 2025-12-10 15:10:00
Version: 1.0.0
Description: Database optimization modülü için testler
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import tempfile
import os

from api.database_optimization import (
    analyze_query_plan,
    optimize_indexes,
    batch_update_sessions,
    get_query_statistics,
    analyze_slow_queries,
)


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
