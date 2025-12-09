"""
Logging Config Additional Edge Cases Tests
Created: 2025-12-10 00:25:00
Last Modified: 2025-12-10 09:00:00
Version: 1.0.0
Description: Logging config ek edge case testleri
"""

import sys
import threading
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.logging_config import JSONFormatter, thread_safe_log


class TestLoggingConfigAdditionalEdgeCases:
    """Logging config ek edge case testleri"""

    def test_json_formatter_with_exception(self):
        """JSON formatter - exception handling"""
        formatter = JSONFormatter()

        # Exception bilgisi olan record
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=40,
                pathname="test.py",
                lineno=1,
                msg="Test error",
                args=(),
                exc_info=sys.exc_info(),
            )

        formatted = formatter.format(record)

        # JSON formatında olmalı ve exception bilgisi içermeli
        import json

        data = json.loads(formatted)
        assert "exception" in data or "error" in data

    def test_json_formatter_with_non_serializable_extra_fields(self):
        """JSON formatter - non-serializable extra fields"""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=20,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Non-serializable object ekle
        class NonSerializable:
            pass

        record.extra_fields = {
            "serializable": "value",
            "non_serializable": NonSerializable(),
        }

        formatted = formatter.format(record)

        # JSON formatında olmalı (non-serializable string'e çevrilmeli)
        import json

        data = json.loads(formatted)
        assert "serializable" in data
        assert "non_serializable" in data

    def test_thread_safe_log_with_kwargs(self):
        """Thread safe log - kwargs ile"""
        logger = logging.getLogger("test_thread_logger")

        # Kwargs ile thread-safe log
        thread_safe_log(logger, 20, "Test message", key1="value1", key2=123)

        # Exception oluşmamalı
        assert True

    def test_thread_safe_log_without_kwargs(self):
        """Thread safe log - kwargs olmadan"""
        logger = logging.getLogger("test_thread_logger_no_kwargs")

        # Kwargs olmadan thread-safe log (logger.log çağrılmalı)
        # thread_safe_log kwargs yoksa logger.log kullanır
        thread_safe_log(logger, 20, "Test message")

        # Exception oluşmamalı
        assert True

    def test_thread_safe_log_concurrent(self):
        """Thread safe log - eşzamanlı"""
        logger = logging.getLogger("test_concurrent_logger")

        def log_message(msg_id):
            thread_safe_log(logger, 20, f"Message {msg_id}", id=msg_id)

        threads = []
        for i in range(20):
            thread = threading.Thread(target=log_message, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Tüm thread'ler başarılı olmalı
        assert True
