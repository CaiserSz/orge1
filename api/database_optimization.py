"""
Database Query Optimization Module
Created: 2025-12-10 15:00:00
Last Modified: 2025-12-10 15:00:00
Version: 1.0.0
Description: Database query optimization utilities - Query plan analysis, index optimization, batch operations
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from api.logging_config import system_logger


def analyze_query_plan(
    conn: sqlite3.Connection, query: str, params: Optional[Tuple] = None
) -> List[Dict[str, Any]]:
    """
    SQL query plan analizi yap

    Args:
        conn: SQLite connection
        query: SQL query
        params: Query parametreleri

    Returns:
        Query plan sonuçları
    """
    try:
        cursor = conn.cursor()
        explain_query = f"EXPLAIN QUERY PLAN {query}"
        cursor.execute(explain_query, params or ())
        rows = cursor.fetchall()

        plan = []
        for row in rows:
            plan.append(
                {
                    "selectid": row[0],
                    "order": row[1],
                    "from": row[2],
                    "detail": row[3],
                }
            )

        return plan
    except Exception as e:
        system_logger.error(f"Query plan analysis error: {e}", exc_info=True)
        return []


def optimize_indexes(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Database index'lerini optimize et ve eksik index'leri ekle

    Args:
        conn: SQLite connection

    Returns:
        Optimization sonuçları
    """
    results = {"created": [], "skipped": [], "errors": []}

    try:
        cursor = conn.cursor()

        # Eksik index'leri kontrol et ve ekle
        indexes_to_create = [
            # exclude_status sorguları için index (status != ?)
            # Not: SQLite'de != için index kullanımı sınırlı, ama composite index yardımcı olabilir
            # Bu durumda status ve start_time composite index'i zaten var (idx_sessions_status_start_time)
            # Ancak exclude_status için daha iyi bir yaklaşım: status IN (...) kullanmak
            # get_current_session için optimize edilmiş index
            # (status, end_time, start_time) composite index
            (
                "idx_sessions_status_end_start",
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_status_end_start
                ON sessions(status, end_time, start_time DESC)
                WHERE end_time IS NULL
                """,
            ),
            # user_id ve status kombinasyonu için index
            (
                "idx_sessions_user_status_start",
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_user_status_start
                ON sessions(user_id, status, start_time DESC)
                """,
            ),
            # session_id lookup için (zaten PRIMARY KEY var ama explicit index ekleyebiliriz)
            # PRIMARY KEY zaten index oluşturur, bu yüzden gerek yok
        ]

        for index_name, create_sql in indexes_to_create:
            try:
                # Index'in var olup olmadığını kontrol et
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name=?
                    """,
                    (index_name,),
                )
                if cursor.fetchone():
                    results["skipped"].append(index_name)
                    continue

                cursor.execute(create_sql)
                conn.commit()
                results["created"].append(index_name)
                system_logger.info(f"Index created: {index_name}")
            except Exception as e:
                results["errors"].append({"index": index_name, "error": str(e)})
                system_logger.error(f"Index creation error ({index_name}): {e}")

        # Index kullanım istatistiklerini al
        cursor.execute(
            """
            SELECT name, sql FROM sqlite_master
            WHERE type='index' AND tbl_name='sessions'
            ORDER BY name
            """
        )
        existing_indexes = cursor.fetchall()
        results["existing_indexes"] = [idx[0] for idx in existing_indexes]

        return results
    except Exception as e:
        system_logger.error(f"Index optimization error: {e}", exc_info=True)
        results["errors"].append({"operation": "optimize_indexes", "error": str(e)})
        return results


def batch_update_sessions(
    conn: sqlite3.Connection,
    updates: List[Dict[str, Any]],
) -> int:
    """
    Birden fazla session'ı tek sorguda güncelle (batch operation)

    Args:
        conn: SQLite connection
        updates: Güncelleme listesi [{"session_id": "...", "field": "value", ...}, ...]

    Returns:
        Güncellenen session sayısı
    """
    if not updates:
        return 0

    try:
        cursor = conn.cursor()
        updated_count = 0

        # Her session için ayrı UPDATE sorgusu çalıştır
        # SQLite'de tek sorguda birden fazla row güncellemek için CASE WHEN kullanılabilir
        # Ancak bu karmaşık olabilir, bu yüzden prepared statement kullanarak batch işlem yapıyoruz

        for update_data in updates:
            session_id = update_data.pop("session_id")
            if not session_id:
                continue

            # UPDATE sorgusu oluştur
            update_fields = []
            update_values = []

            for field, value in update_data.items():
                update_fields.append(f"{field} = ?")
                update_values.append(value)

            if not update_fields:
                continue

            update_values.append(session_id)
            update_sql = (
                f"UPDATE sessions SET {', '.join(update_fields)} WHERE session_id = ?"
            )

            cursor.execute(update_sql, update_values)
            if cursor.rowcount > 0:
                updated_count += 1

        conn.commit()
        return updated_count
    except Exception as e:
        system_logger.error(f"Batch update error: {e}", exc_info=True)
        conn.rollback()
        return 0


def get_query_statistics(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Database query istatistiklerini al

    Args:
        conn: SQLite connection

    Returns:
        Query istatistikleri
    """
    try:
        cursor = conn.cursor()

        # Table size
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]

        # session_events tablosu varsa say
        try:
            cursor.execute("SELECT COUNT(*) FROM session_events")
            event_count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            event_count = 0

        # Index count
        cursor.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='index' AND tbl_name IN ('sessions', 'session_events')
            """
        )
        index_count = cursor.fetchone()[0]

        # Database size (approximate)
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        db_size_bytes = page_count * page_size

        return {
            "session_count": session_count,
            "event_count": event_count,
            "index_count": index_count,
            "database_size_bytes": db_size_bytes,
            "database_size_mb": round(db_size_bytes / (1024 * 1024), 2),
        }
    except Exception as e:
        system_logger.error(f"Query statistics error: {e}", exc_info=True)
        return {}


def vacuum_database(conn: sqlite3.Connection) -> bool:
    """
    Database'i optimize et (VACUUM)

    Args:
        conn: SQLite connection

    Returns:
        Başarılı ise True
    """
    try:
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        system_logger.info("Database vacuum completed")
        return True
    except Exception as e:
        system_logger.error(f"Database vacuum error: {e}", exc_info=True)
        return False


def analyze_slow_queries(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Yavaş sorguları analiz et (query plan'a göre)

    Args:
        conn: SQLite connection

    Returns:
        Yavaş sorgu analizleri
    """
    slow_queries = []

    # Yaygın sorguları analiz et
    common_queries = [
        {
            "name": "get_sessions_with_status",
            "query": "SELECT * FROM sessions WHERE status = ? ORDER BY start_time DESC LIMIT ? OFFSET ?",
            "params": ("ACTIVE", 100, 0),
        },
        {
            "name": "get_sessions_with_user",
            "query": "SELECT * FROM sessions WHERE user_id = ? ORDER BY start_time DESC LIMIT ? OFFSET ?",
            "params": ("test_user", 100, 0),
        },
        {
            "name": "get_current_session",
            "query": "SELECT * FROM sessions WHERE status = 'ACTIVE' AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
            "params": None,
        },
        {
            "name": "get_session_count",
            "query": "SELECT COUNT(*) FROM sessions WHERE status = ?",
            "params": ("ACTIVE",),
        },
    ]

    for query_info in common_queries:
        try:
            plan = analyze_query_plan(conn, query_info["query"], query_info["params"])
            slow_queries.append(
                {
                    "name": query_info["name"],
                    "query": query_info["query"],
                    "plan": plan,
                    "uses_index": any(
                        "USING INDEX" in str(p.get("detail", "")) for p in plan
                    ),
                }
            )
        except Exception as e:
            system_logger.error(
                f"Slow query analysis error ({query_info['name']}): {e}"
            )

    return slow_queries
