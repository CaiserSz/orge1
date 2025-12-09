"""
Logging Config Module Tests
Created: 2025-12-09 23:30:00
Last Modified: 2025-12-09 23:30:00
Version: 1.0.0
Description: Logging config modülü için unit testler ve edge case testleri
"""

import pytest
import sys
import logging
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.logging_config import (
    api_logger, esp32_logger, system_logger,
    log_api_request, log_esp32_message, log_event
)


class TestLoggingConfig:
    """Logging config modülü testleri"""

    def setup_method(self):
        """Her test öncesi"""
        # Logger'ları temizle
        pass

    def test_loggers_exist(self):
        """Logger'lar mevcut mu?"""
        assert api_logger is not None
        assert esp32_logger is not None
        assert system_logger is not None

    def test_loggers_have_handlers(self):
        """Logger'ların handler'ları var mı?"""
        assert len(api_logger.handlers) > 0
        assert len(esp32_logger.handlers) > 0
        assert len(system_logger.handlers) > 0

    def test_log_api_request_success(self):
        """log_api_request - başarılı loglama"""
        with patch.object(api_logger, 'handle') as mock_handle:
            log_api_request(
                method="GET",
                path="/api/status",
                status_code=200,
                response_time=0.1
            )

            mock_handle.assert_called_once()
            call_args = mock_handle.call_args
            assert call_args is not None

    def test_log_api_request_with_extra_fields(self):
        """log_api_request - ekstra field'lar"""
        with patch.object(api_logger, 'handle') as mock_handle:
            log_api_request(
                method="POST",
                path="/api/charge/start",
                status_code=200,
                response_time=0.2,
                user_id="test-user",
                api_key="test-key"
            )

            mock_handle.assert_called_once()

    def test_log_api_request_exception_handling(self):
        """log_api_request - exception handling"""
        with patch.object(api_logger, 'handle', side_effect=Exception("Log error")):
            # Exception oluşsa bile uygulama çalışmaya devam etmeli
            try:
                log_api_request(
                    method="GET",
                    path="/api/status",
                    status_code=200,
                    response_time=0.1
                )
            except Exception:
                pytest.fail("log_api_request exception'ı yakalamalı")

    def test_log_esp32_message_success(self):
        """log_esp32_message - başarılı loglama"""
        with patch.object(esp32_logger, 'handle') as mock_handle:
            log_esp32_message(
                message_type="status",
                direction="rx",
                data="Test message"
            )

            mock_handle.assert_called_once()

    def test_log_esp32_message_with_data(self):
        """log_esp32_message - data ile"""
        with patch.object(esp32_logger, 'handle') as mock_handle:
            log_esp32_message(
                message_type="status",
                direction="rx",
                data={"STATE": 1, "CP": 1}
            )

            mock_handle.assert_called_once()

    def test_log_esp32_message_exception_handling(self):
        """log_esp32_message - exception handling"""
        with patch.object(esp32_logger, 'handle', side_effect=Exception("Log error")):
            # Exception oluşsa bile uygulama çalışmaya devam etmeli
            try:
                log_esp32_message(
                    message_type="status",
                    direction="rx",
                    data="Test"
                )
            except Exception:
                pytest.fail("log_esp32_message exception'ı yakalamalı")

    def test_log_event_success(self):
        """log_event - başarılı loglama"""
        with patch.object(system_logger, 'handle') as mock_handle:
            log_event(
                event_type="CHARGE_STARTED",
                event_data={"user_id": "test-user"}
            )

            mock_handle.assert_called_once()

    def test_log_event_with_kwargs(self):
        """log_event - kwargs ile"""
        with patch.object(system_logger, 'handle') as mock_handle:
            log_event(
                event_type="CHARGE_STARTED",
                event_data={"user_id": "test-user"},
                level=logging.INFO,
                extra_field="extra_value"
            )

            mock_handle.assert_called_once()

    def test_log_event_error_level(self):
        """log_event - error seviyesi"""
        with patch.object(system_logger, 'handle') as mock_handle:
            log_event(
                event_type="FAULT_DETECTED",
                event_data={"fault_type": "hard"},
                level=logging.ERROR
            )

            mock_handle.assert_called_once()
            # LogRecord'un level'ı ERROR olmalı
            call_args = mock_handle.call_args[0][0]
            assert call_args.levelno == logging.ERROR

    def test_log_event_warning_level(self):
        """log_event - warning seviyesi"""
        with patch.object(system_logger, 'handle') as mock_handle:
            log_event(
                event_type="WARNING_EVENT",
                event_data={"warning": "test"},
                level=logging.WARNING
            )

            mock_handle.assert_called_once()
            call_args = mock_handle.call_args[0][0]
            assert call_args.levelno == logging.WARNING

    def test_log_event_debug_level(self):
        """log_event - debug seviyesi"""
        with patch.object(system_logger, 'handle') as mock_handle:
            log_event(
                event_type="DEBUG_EVENT",
                event_data={"debug": "test"},
                level=logging.DEBUG
            )

            mock_handle.assert_called_once()
            call_args = mock_handle.call_args[0][0]
            assert call_args.levelno == logging.DEBUG

    def test_log_event_without_event_data(self):
        """log_event - event_data olmadan"""
        with patch.object(system_logger, 'handle') as mock_handle:
            log_event(
                event_type="SIMPLE_EVENT"
            )

            mock_handle.assert_called_once()

    def test_log_event_exception_handling(self):
        """log_event - exception handling"""
        with patch.object(system_logger, 'handle', side_effect=Exception("Log error")):
            # Exception oluşsa bile uygulama çalışmaya devam etmeli
            try:
                log_event(
                    event_type="TEST_EVENT",
                    event_data={"test": "data"}
                )
            except Exception:
                pytest.fail("log_event exception'ı yakalamalı")

    def test_log_event_nested_exception_handling(self):
        """log_event - nested exception handling"""
        # İlk exception sonrası ikinci exception oluşursa
        with patch.object(system_logger, 'handle', side_effect=Exception("Log error")):
            with patch.object(system_logger, 'error', side_effect=Exception("Error log error")):
                # Her iki exception da yakalanmalı
                try:
                    log_event(
                        event_type="TEST_EVENT",
                        event_data={"test": "data"}
                    )
                except Exception:
                    pytest.fail("log_event nested exception'ı yakalamalı")

    def test_log_api_request_thread_safety(self):
        """log_api_request - thread safety"""
        import threading

        results = []

        def log_in_thread(thread_id):
            try:
                log_api_request(
                    method="GET",
                    path=f"/api/test/{thread_id}",
                    status_code=200,
                    response_time=0.1
                )
                results.append(True)
            except Exception:
                results.append(False)

        threads = []
        for i in range(10):
            thread = threading.Thread(target=log_in_thread, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Tüm thread'ler başarılı olmalı
        assert all(results)
        assert len(results) == 10

    def test_log_event_thread_safety(self):
        """log_event - thread safety"""
        import threading

        results = []

        def log_in_thread(thread_id):
            try:
                log_event(
                    event_type=f"TEST_EVENT_{thread_id}",
                    event_data={"thread_id": thread_id}
                )
                results.append(True)
            except Exception:
                results.append(False)

        threads = []
        for i in range(10):
            thread = threading.Thread(target=log_in_thread, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Tüm thread'ler başarılı olmalı
        assert all(results)
        assert len(results) == 10

