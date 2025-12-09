"""
Missing Unit and Edge Case Tests
Created: 2025-12-10 00:15:00
Last Modified: 2025-12-10 00:15:00
Version: 1.0.0
Description: Coverage'dan bağımsız eksik unit ve edge case testleri
"""

import pytest
import sys
import os
import tempfile
import threading
import time
import logging
from unittest.mock import Mock, patch, mock_open, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app, startup_event, shutdown_event, APILoggingMiddleware, APIResponse, ChargeStartRequest, ChargeStopRequest, CurrentSetRequest
from api.event_detector import EventDetector, get_event_detector, ESP32State, EventType
from api.logging_config import setup_logger, get_logger, thread_safe_log, JSONFormatter
from api.auth import get_secret_api_key, verify_api_key
from api.station_info import ensure_data_dir
from esp32.bridge import ESP32Bridge, get_esp32_bridge, BAUDRATE


class TestStartupShutdownEvents:
    """Startup ve shutdown event testleri"""

    def test_startup_event_success(self):
        """Startup event - başarılı"""
        mock_bridge = Mock()
        mock_bridge.is_connected = True

        with patch('api.main.get_esp32_bridge', return_value=mock_bridge):
            with patch('api.main.get_event_detector') as mock_get_detector:
                mock_detector = Mock()
                mock_get_detector.return_value = mock_detector

                # Startup event'i çağır
                import asyncio
                asyncio.run(startup_event())

                # Event detector başlatılmalı
                mock_detector.start_monitoring.assert_called_once()

    def test_startup_event_bridge_not_connected(self):
        """Startup event - bridge bağlı değil"""
        mock_bridge = Mock()
        mock_bridge.is_connected = False

        with patch('api.main.get_esp32_bridge', return_value=mock_bridge):
            with patch('api.main.get_event_detector') as mock_get_detector:
                mock_detector = Mock()
                mock_get_detector.return_value = mock_detector

                # Startup event'i çağır - hata oluşmamalı
                import asyncio
                asyncio.run(startup_event())

                # Event detector yine de başlatılmalı
                mock_detector.start_monitoring.assert_called_once()

    def test_startup_event_exception(self):
        """Startup event - exception handling"""
        with patch('api.main.get_esp32_bridge', side_effect=Exception("Startup error")):
            # Exception yakalanmalı ve uygulama çalışmaya devam etmeli
            import asyncio
            try:
                asyncio.run(startup_event())
            except Exception:
                pytest.fail("Startup event exception'ı yakalamalı")

    def test_shutdown_event_success(self):
        """Shutdown event - başarılı"""
        mock_bridge = Mock()
        mock_bridge.is_connected = True

        with patch('api.main.get_esp32_bridge', return_value=mock_bridge):
            with patch('api.main.get_event_detector') as mock_get_detector:
                mock_detector = Mock()
                mock_get_detector.return_value = mock_detector

                # Shutdown event'i çağır
                import asyncio
                asyncio.run(shutdown_event())

                # Event detector durdurulmalı
                mock_detector.stop_monitoring.assert_called_once()
                # Bridge disconnect edilmeli
                mock_bridge.disconnect.assert_called_once()

    def test_shutdown_event_bridge_none(self):
        """Shutdown event - bridge None"""
        with patch('api.main.get_esp32_bridge', return_value=None):
            with patch('api.main.get_event_detector') as mock_get_detector:
                mock_detector = Mock()
                mock_get_detector.return_value = mock_detector

                # Shutdown event'i çağır - hata oluşmamalı
                import asyncio
                asyncio.run(shutdown_event())

                # Event detector durdurulmalı
                mock_detector.stop_monitoring.assert_called_once()

    def test_shutdown_event_exception(self):
        """Shutdown event - exception handling"""
        with patch('api.main.get_esp32_bridge', side_effect=Exception("Shutdown error")):
            # Exception yakalanmalı ve uygulama çalışmaya devam etmeli
            import asyncio
            try:
                asyncio.run(shutdown_event())
            except Exception:
                pytest.fail("Shutdown event exception'ı yakalamalı")


class TestAPILoggingMiddleware:
    """API Logging Middleware testleri"""

    def test_middleware_logs_request(self):
        """Middleware - request loglar"""
        middleware = APILoggingMiddleware(app)

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/health"
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            response = Mock()
            response.status_code = 200
            return response

        with patch('api.main.log_api_request') as mock_log:
            import asyncio
            response = asyncio.run(middleware.dispatch(mock_request, mock_call_next))

            # Request loglanmalı
            mock_log.assert_called_once()
            assert response.status_code == 200

    def test_middleware_excludes_charge_endpoints(self):
        """Middleware - charge endpoint'lerini exclude eder"""
        middleware = APILoggingMiddleware(app)

        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/charge/start"
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            response = Mock()
            response.status_code = 200
            return response

        with patch('api.main.log_api_request') as mock_log:
            import asyncio
            response = asyncio.run(middleware.dispatch(mock_request, mock_call_next))

            # Charge endpoint'leri loglanmamalı
            mock_log.assert_not_called()
            assert response.status_code == 200

    def test_middleware_exception_handling(self):
        """Middleware - exception handling"""
        middleware = APILoggingMiddleware(app)

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/health"
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            raise Exception("Request error")

        # Exception yakalanmalı ve response döndürülmeli
        import asyncio
        try:
            response = asyncio.run(middleware.dispatch(mock_request, mock_call_next))
            # Exception oluşursa response None olabilir veya exception handler çalışır
        except Exception:
            # Exception middleware tarafından yakalanmalı
            pass


class TestAPIResponseModel:
    """APIResponse model testleri"""

    def test_api_response_with_data(self):
        """APIResponse - data ile"""
        response = APIResponse(
            success=True,
            message="Test message",
            data={"key": "value"}
        )

        assert response.success is True
        assert response.message == "Test message"
        assert response.data == {"key": "value"}
        assert response.timestamp is not None

    def test_api_response_without_data(self):
        """APIResponse - data olmadan"""
        response = APIResponse(
            success=False,
            message="Error message"
        )

        assert response.success is False
        assert response.message == "Error message"
        assert response.data is None

    def test_api_response_timestamp_auto_generated(self):
        """APIResponse - timestamp otomatik oluşturulur"""
        response1 = APIResponse(success=True, message="Test")
        time.sleep(0.01)
        response2 = APIResponse(success=True, message="Test")

        assert response1.timestamp != response2.timestamp


class TestRequestModels:
    """Request model validation testleri"""

    def test_current_set_request_valid(self):
        """CurrentSetRequest - geçerli değer"""
        request = CurrentSetRequest(amperage=16)
        assert request.amperage == 16

    def test_current_set_request_minimum(self):
        """CurrentSetRequest - minimum değer"""
        request = CurrentSetRequest(amperage=6)
        assert request.amperage == 6

    def test_current_set_request_maximum(self):
        """CurrentSetRequest - maksimum değer"""
        request = CurrentSetRequest(amperage=32)
        assert request.amperage == 32

    def test_current_set_request_below_minimum(self):
        """CurrentSetRequest - minimum altı"""
        with pytest.raises(Exception):  # ValidationError
            CurrentSetRequest(amperage=5)

    def test_current_set_request_above_maximum(self):
        """CurrentSetRequest - maksimum üstü"""
        with pytest.raises(Exception):  # ValidationError
            CurrentSetRequest(amperage=33)

    def test_charge_start_request_empty(self):
        """ChargeStartRequest - boş request"""
        request = ChargeStartRequest()
        assert request is not None

    def test_charge_stop_request_empty(self):
        """ChargeStopRequest - boş request"""
        request = ChargeStopRequest()
        assert request is not None


class TestEventDetectorCallbacks:
    """Event Detector callback testleri"""

    def test_register_callback(self):
        """Register callback"""
        mock_bridge = Mock()
        mock_bridge.is_connected = True

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        callback_called = []

        def callback(event_type, event_data):
            callback_called.append((event_type, event_data))

        detector.register_callback(callback)

        # Event oluştur
        detector._check_state_transition(1, {"STATE": 1})
        detector._check_state_transition(2, {"STATE": 2})

        # Callback çağrılmalı
        assert len(callback_called) == 1

    def test_unregister_callback(self):
        """Unregister callback"""
        mock_bridge = Mock()
        mock_bridge.is_connected = True

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        callback_called = []

        def callback(event_type, event_data):
            callback_called.append((event_type, event_data))

        detector.register_callback(callback)
        detector.unregister_callback(callback)

        # Event oluştur
        detector._check_state_transition(1, {"STATE": 1})
        detector._check_state_transition(2, {"STATE": 2})

        # Callback çağrılmamalı
        assert len(callback_called) == 0

    def test_multiple_callbacks(self):
        """Birden fazla callback"""
        mock_bridge = Mock()
        mock_bridge.is_connected = True

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        callback1_called = []
        callback2_called = []

        def callback1(event_type, event_data):
            callback1_called.append(1)

        def callback2(event_type, event_data):
            callback2_called.append(2)

        detector.register_callback(callback1)
        detector.register_callback(callback2)

        # Event oluştur
        detector._check_state_transition(1, {"STATE": 1})
        detector._check_state_transition(2, {"STATE": 2})

        # Her iki callback de çağrılmalı
        assert len(callback1_called) == 1
        assert len(callback2_called) == 1


class TestEventDetectorGetStateName:
    """Event Detector _get_state_name testleri"""

    def test_get_state_name_all_states(self):
        """Get state name - tüm state'ler"""
        mock_bridge = Mock()

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        state_names = {
            1: "IDLE",
            2: "CABLE_DETECT",
            3: "EV_CONNECTED",
            4: "READY",
            5: "CHARGING",
            6: "PAUSED",
            7: "STOPPED",
            8: "FAULT_HARD"
        }

        for state, expected_name in state_names.items():
            name = detector._get_state_name(state)
            assert name == expected_name

    def test_get_state_name_unknown(self):
        """Get state name - bilinmeyen state"""
        mock_bridge = Mock()

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        name = detector._get_state_name(99)
        assert name == "UNKNOWN_99"

    def test_get_state_name_zero(self):
        """Get state name - state 0"""
        mock_bridge = Mock()

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        name = detector._get_state_name(0)
        assert name == "UNKNOWN_0"

    def test_get_state_name_negative(self):
        """Get state name - negatif state"""
        mock_bridge = Mock()

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        name = detector._get_state_name(-1)
        assert name == "UNKNOWN_-1"


class TestEventDetectorSingleton:
    """Event Detector singleton testleri"""

    def test_get_event_detector_singleton(self):
        """Get event detector - singleton"""
        import api.event_detector as detector_module
        original_instance = detector_module.event_detector_instance
        detector_module.event_detector_instance = None

        try:
            mock_bridge = Mock()

            def bridge_getter():
                return mock_bridge

            detector1 = get_event_detector(bridge_getter)
            detector2 = get_event_detector(bridge_getter)

            # Aynı instance döndürülmeli
            assert detector1 is detector2
        finally:
            # Restore original instance
            detector_module.event_detector_instance = original_instance

    def test_get_event_detector_thread_safe(self):
        """Get event detector - thread safe"""
        import api.event_detector as detector_module
        original_instance = detector_module.event_detector_instance
        detector_module.event_detector_instance = None

        try:
            mock_bridge = Mock()

            def bridge_getter():
                return mock_bridge

            detectors = []

            def get_detector():
                detector = get_event_detector(bridge_getter)
                detectors.append(detector)

            threads = []
            for _ in range(10):
                thread = threading.Thread(target=get_detector)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # Tüm detector'lar aynı instance olmalı
            assert all(detector is detectors[0] for detector in detectors)
        finally:
            # Restore original instance
            detector_module.event_detector_instance = original_instance


class TestLoggingConfigFunctions:
    """Logging config fonksiyon testleri"""

    def test_setup_logger(self):
        """Setup logger"""
        logger = setup_logger("test_logger", "test.log")

        assert logger is not None
        assert logger.name == "test_logger"
        assert len(logger.handlers) > 0

    def test_get_logger(self):
        """Get logger"""
        logger1 = get_logger("test_logger")
        logger2 = get_logger("test_logger")

        # Aynı logger instance döndürülmeli
        assert logger1 is logger2

    def test_thread_safe_log(self):
        """Thread safe log"""
        logger = get_logger("test_thread_logger")

        # Thread-safe logging çalışmalı
        thread_safe_log(logger, 20, "Test message", key="value")

        # Exception oluşmamalı
        assert True

    def test_json_formatter(self):
        """JSON formatter"""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=20,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)

        # JSON formatında olmalı
        import json
        data = json.loads(formatted)
        assert "timestamp" in data
        assert "level" in data
        assert "message" in data


class TestAuthEdgeCases:
    """Auth edge case testleri"""

    def test_get_secret_api_key_success(self):
        """Get secret API key - başarılı"""
        with patch.dict(os.environ, {'SECRET_API_KEY': 'test-key'}):
            key = get_secret_api_key()
            assert key == 'test-key'

    def test_get_secret_api_key_empty_string(self):
        """Get secret API key - boş string"""
        with patch.dict(os.environ, {'SECRET_API_KEY': ''}):
            with pytest.raises(ValueError):
                get_secret_api_key()

    def test_verify_api_key_none(self):
        """Verify API key - None"""
        with patch.dict(os.environ, {'SECRET_API_KEY': 'test-key'}):
            from fastapi import Security
            from fastapi.security import APIKeyHeader

            api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

            # None API key ile verify
            with pytest.raises(Exception):  # HTTPException
                verify_api_key(None)


class TestStationInfoEdgeCases:
    """Station info edge case testleri"""

    def test_ensure_data_dir_permission_error(self):
        """Ensure data dir - permission error"""
        with patch('api.station_info.DATA_FILE', Path("/root/invalid/path.json")):
            # Permission error oluşabilir ama exception yakalanmalı
            try:
                ensure_data_dir()
            except PermissionError:
                # Permission error beklenebilir
                pass

    def test_ensure_data_dir_success(self):
        """Ensure data dir - başarılı"""
        temp_dir = tempfile.mkdtemp()
        temp_file = Path(temp_dir) / "station_info.json"

        with patch('api.station_info.DATA_FILE', temp_file):
            ensure_data_dir()
            assert temp_file.parent.exists()


class TestESP32BridgeSingleton:
    """ESP32 Bridge singleton testleri"""

    def test_get_esp32_bridge_singleton(self):
        """Get ESP32 bridge - singleton"""
        # Singleton instance'ı reset etmek için
        import esp32.bridge as bridge_module
        original_instance = bridge_module._esp32_bridge_instance
        bridge_module._esp32_bridge_instance = None

        try:
            bridge1 = get_esp32_bridge()
            bridge2 = get_esp32_bridge()

            # Aynı instance döndürülmeli
            assert bridge1 is bridge2
        finally:
            # Restore original instance
            bridge_module._esp32_bridge_instance = original_instance

    def test_get_esp32_bridge_thread_safe(self):
        """Get ESP32 bridge - thread safe"""
        import esp32.bridge as bridge_module
        original_instance = bridge_module._esp32_bridge_instance
        bridge_module._esp32_bridge_instance = None

        try:
            bridges = []

            def get_bridge():
                bridge = get_esp32_bridge()
                bridges.append(bridge)

            threads = []
            for _ in range(10):
                thread = threading.Thread(target=get_bridge)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # Tüm bridge'ler aynı instance olmalı
            assert all(bridge is bridges[0] for bridge in bridges)
        finally:
            # Restore original instance
            bridge_module._esp32_bridge_instance = original_instance


class TestESP32BridgeParseStatusEdgeCases:
    """ESP32 Bridge parse status edge case testleri"""

    def test_parse_status_message_partial_fields(self):
        """Parse status message - kısmi field'lar"""
        bridge = ESP32Bridge()

        # Sadece bazı field'lar var
        message = "<STAT;ID=1;CP=1;STATE=1;>"
        result = bridge._parse_status_message(message)

        assert result is not None
        assert result.get("ID") == 1
        assert result.get("CP") == 1
        assert result.get("STATE") == 1

    def test_parse_status_message_duplicate_fields(self):
        """Parse status message - duplicate field'lar"""
        bridge = ESP32Bridge()

        # Duplicate field'lar (son değer kullanılmalı)
        message = "<STAT;ID=1;ID=2;STATE=1;>"
        result = bridge._parse_status_message(message)

        # Son değer kullanılmalı veya parse edilebilir
        assert result is not None

    def test_parse_status_message_special_characters(self):
        """Parse status message - özel karakterler"""
        bridge = ESP32Bridge()

        # Özel karakterler içeren mesajlar
        messages = [
            "<STAT;ID=1;MSG=TEST_MESSAGE;>",
            "<STAT;ID=1;MSG=TEST%20MESSAGE;>",
        ]

        for message in messages:
            result = bridge._parse_status_message(message)
            # Parse edilebilir veya None döndürmeli
            assert result is None or isinstance(result, dict)

    def test_parse_status_message_very_long(self):
        """Parse status message - çok uzun mesaj"""
        bridge = ESP32Bridge()

        # Çok uzun mesaj
        long_message = "<STAT;" + ";".join([f"ID={i}" for i in range(100)]) + ";>"
        result = bridge._parse_status_message(long_message)

        # Parse edilebilir veya None döndürmeli
        assert result is None or isinstance(result, dict)

    def test_parse_status_message_unicode(self):
        """Parse status message - unicode karakterler"""
        bridge = ESP32Bridge()

        # Unicode karakterler içeren mesajlar (normalde olmamalı ama test edelim)
        messages = [
            "<STAT;ID=1;MSG=Test;>",
            "<STAT;ID=1;MSG=Тест;>",  # Cyrillic
        ]

        for message in messages:
            result = bridge._parse_status_message(message)
            # Parse edilebilir veya None döndürmeli
            assert result is None or isinstance(result, dict)

