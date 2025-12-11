"""
Maintenance Queries Module
Created: 2025-12-10 21:09:49
Last Modified: 2025-12-10 21:09:49
Version: 1.0.0
Description: Database bakım ve temizlik operasyonları mixin'i.
"""

from api.logging_config import system_logger


class MaintenanceQueryMixin:
    """Database bakım operasyonlarını sağlayan mixin."""

    def cleanup_old_sessions(self, max_sessions: int = 1000) -> int:
        """
        Eski session kayıtlarını temizler.

        Returns:
            Silinen session sayısı.
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM sessions")
                total_count = cursor.fetchone()[0]

                if total_count <= max_sessions:
                    return 0

                to_remove = int(total_count * 0.1)

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
            except Exception as exc:
                system_logger.error(f"Cleanup old sessions error: {exc}", exc_info=True)
                conn.rollback()
                return 0
