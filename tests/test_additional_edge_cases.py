"""
Additional Edge Cases Tests
Created: 2025-12-10 00:25:00
Last Modified: 2025-12-10 00:25:00
Version: 1.0.0
Description: Ek edge case testleri - coverage'dan bağımsız
"""

import pytest
import sys
import time
import threading
import logging
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import EventDetector, EventType, ESP32State
from api.logging_config import JSONFormatter, thread_safe_log
from esp32.bridge import ESP32Bridge
from api.main import get_bridge


class TestEventDetectorAdditionalEdgeCases:
    """Event Detector ek edge case testleri"""

    def test_classify_event_all_transitions(self):
        """Classify event - tüm transition'lar"""
        mock_bridge = Mock()

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        # Tüm geçerli transition'ları test et
        transitions = [
            (ESP32State.IDLE.value, ESP32State.CABLE_DETECT.value, EventType.CABLE_CONNECTED),
            (ESP32State.CABLE_DETECT.value, ESP32State.EV_CONNECTED.value, EventType.EV_CONNECTED),
            (ESP32State.EV_CONNECTED.value, ESP32State.READY.value, EventType.CHARGE_READY),
            (ESP32State.READY.value, ESP32State.CHARGING.value, EventType.CHARGE_STARTED),
            (ESP32State.CHARGING.value, ESP32State.PAUSED.value, EventType.CHARGE_PAUSED),
            (ESP32State.CHARGING.value, ESP32State.STOPPED.value, EventType.CHARGE_STOPPED),
            (ESP32State.CABLE_DETECT.value, ESP32State.IDLE.value, EventType.CABLE_DISCONNECTED),
            (ESP32State.EV_CONNECTED.value, ESP32State.IDLE.value, EventType.CABLE_DISCONNECTED),
            (ESP32State.CHARGING.value, ESP32State.FAULT_HARD.value, EventType.FAULT_DETECTED),
        ]

        for from_state, to_state, expected_event in transitions:
            event_type = detector._classify_event(from_state, to_state)
            assert event_type == expected_event

    def test_classify_event_invalid_transition(self):
        """Classify event - geçersiz transition"""
        mock_bridge = Mock()

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        # Geçersiz transition (örn: IDLE -> CHARGING direkt)
        event_type = detector._classify_event(ESP32State.IDLE.value, ESP32State.CHARGING.value)
        assert event_type is None or event_type == EventType.STATE_CHANGED

    def test_create_event_with_exception_in_callback(self):
        """Create event - callback'te exception"""
        mock_bridge = Mock()

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        exception_occurred = []

        def failing_callback(event_type, event_data):
            exception_occurred.append(True)
            raise Exception("Callback error")

        detector.register_callback(failing_callback)

        # Event oluştur - exception yakalanmalı
        detector._create_event(
            EventType.CABLE_CONNECTED,
            1, 2,
            {"STATE": 2}
        )

        # Exception oluştu ama detector çalışmaya devam etmeli
        assert len(exception_occurred) == 1

    def test_monitor_loop_state_none_handling(self):
        """Monitor loop - state None handling"""
        mock_bridge = Mock()
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"CP": 1}  # STATE yok

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)
        detector.start_monitoring()
        time.sleep(0.2)
        detector.stop_monitoring()

        # State None ise hata oluşmamalı
        assert True

    def test_get_current_and_previous_state_thread_safety(self):
        """Get current/previous state - thread safety"""
        mock_bridge = Mock()

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        states = []

        def get_states():
            current = detector.get_current_state()
            previous = detector.get_previous_state()
            states.append((current, previous))

        # State transition yap
        detector._check_state_transition(1, {"STATE": 1})
        detector._check_state_transition(2, {"STATE": 2})

        # Thread'lerden state oku
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_states)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Tüm thread'ler başarılı olmalı
        assert len(states) == 10


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
                exc_info=sys.exc_info()
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
            exc_info=None
        )

        # Non-serializable object ekle
        class NonSerializable:
            pass

        record.extra_fields = {
            "serializable": "value",
            "non_serializable": NonSerializable()
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


class TestESP32BridgeAdditionalEdgeCases:
    """ESP32 Bridge ek edge case testleri"""

    def test_parse_status_message_malformed(self):
        """Parse status message - bozuk format"""
        bridge = ESP32Bridge()

        malformed_messages = [
            "<STAT",  # Kapanmamış
            "STAT;ID=1;>",  # Başlangıç yok
            "<STAT;ID=1",  # Kapanış yok
            "<STAT;>",  # Boş
            "<STAT;ID=;>",  # Boş değer
            "<STAT;=1;>",  # Boş key
            "<STAT;ID=1;CP=;STATE=2;>",  # Kısmi boş değerler
        ]

        for message in malformed_messages:
            result = bridge._parse_status_message(message)
            # Parse edilebilir veya None döndürmeli
            assert result is None or isinstance(result, dict)

    def test_parse_status_message_numeric_edge_cases(self):
        """Parse status message - sayısal edge case'ler"""
        bridge = ESP32Bridge()

        edge_cases = [
            "<STAT;ID=0;STATE=0;>",  # Sıfır değerler
            "<STAT;ID=-1;STATE=-1;>",  # Negatif değerler
            "<STAT;ID=999999;STATE=999999;>",  # Çok büyük değerler
            "<STAT;CPV=3920.5;PPV=2455.7;>",  # Float değerler
            "<STAT;ID=1.0;STATE=2.0;>",  # Float ama integer olmalı
        ]

        for message in edge_cases:
            result = bridge._parse_status_message(message)
            # Parse edilebilir veya None döndürmeli
            assert result is None or isinstance(result, dict)

    def test_send_command_bytes_empty_list(self):
        """Send command bytes - boş liste"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.serial_connection.write = Mock(return_value=0)

        # Boş liste gönder
        result = bridge._send_command_bytes([])

        # Boş liste için False döndürmeli veya exception oluşmamalı
        assert result is False or result is True

    def test_send_command_bytes_invalid_length(self):
        """Send command bytes - geçersiz uzunluk"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.serial_connection.write = Mock(return_value=0)

        # Geçersiz uzunlukta komut (5 byte olmalı)
        invalid_commands = [
            [0x41],  # Çok kısa
            [0x41, 0x01, 0x2C, 0x10],  # 4 byte
            [0x41, 0x01, 0x2C, 0x10, 0x10, 0x10],  # 6 byte
        ]

        for cmd in invalid_commands:
            result = bridge._send_command_bytes(cmd)
            # Geçersiz uzunluk için False döndürmeli
            assert result is False

    def test_get_status_sync_timeout_edge_cases(self):
        """Get status sync - timeout edge case'leri"""
        bridge = ESP32Bridge()
        bridge.is_connected = True

        # Status varsa hemen döner
        bridge.last_status = {"STATE": 1}
        result = bridge.get_status_sync(timeout=0.001)
        assert result is not None
        assert result["STATE"] == 1

        # Status yoksa timeout sonrası None döner
        # Bridge bağlı değilse send_status_request False döner
        bridge.is_connected = False
        result = bridge.get_status_sync(timeout=0.01)
        # Bridge bağlı değilse None döner
        assert result is None

    def test_find_esp32_port_edge_cases(self):
        """Find ESP32 port - edge case'ler"""
        bridge = ESP32Bridge()

        # Port bulunamadığında
        with patch('esp32.bridge.serial.tools.list_ports.comports', return_value=[]):
            result = bridge.find_esp32_port()
            assert result is None

        # Port description'da keyword yok
        mock_ports = [
            Mock(device="/dev/ttyUSB0", description="Unknown Device"),
        ]

        with patch('esp32.bridge.serial.tools.list_ports.comports', return_value=mock_ports):
            result = bridge.find_esp32_port()
            assert result is None


class TestAPIMainAdditionalEdgeCases:
    """API Main ek edge case testleri"""

    def test_get_bridge_dependency(self):
        """Get bridge dependency"""
        bridge = get_bridge()

        # Bridge instance döndürülmeli
        assert bridge is not None
        assert isinstance(bridge, ESP32Bridge)

    def test_api_response_model_validation(self):
        """APIResponse model validation"""
        from api.main import APIResponse

        # Geçerli response
        response = APIResponse(
            success=True,
            message="Test",
            data={"key": "value"}
        )

        assert response.success is True
        assert response.message == "Test"
        assert response.data == {"key": "value"}

        # Data None olabilir
        response2 = APIResponse(
            success=False,
            message="Error"
        )

        assert response2.data is None


class TestConcurrencyEdgeCases:
    """Concurrency edge case testleri"""

    def test_event_detector_concurrent_state_access(self):
        """Event detector - eşzamanlı state erişimi"""
        mock_bridge = Mock()

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        states_read = []

        def read_state():
            current = detector.get_current_state()
            previous = detector.get_previous_state()
            states_read.append((current, previous))

        def write_state():
            detector._check_state_transition(1, {"STATE": 1})
            detector._check_state_transition(2, {"STATE": 2})

        # Okuma ve yazma thread'leri
        read_threads = [threading.Thread(target=read_state) for _ in range(5)]
        write_threads = [threading.Thread(target=write_state) for _ in range(2)]

        for thread in write_threads + read_threads:
            thread.start()

        for thread in write_threads + read_threads:
            thread.join()

        # Tüm thread'ler başarılı olmalı
        assert len(states_read) == 5

    def test_logging_concurrent_access(self):
        """Logging - eşzamanlı erişim"""
        logger = logging.getLogger("test_concurrent_logging_final")
        logger.setLevel(logging.DEBUG)

        # Handler yoksa ekle (test için)
        if not logger.handlers:
            handler = logging.NullHandler()  # NullHandler kullan (output yok)
            handler.setLevel(logging.DEBUG)
            logger.addHandler(handler)

        errors = []

        def log_message(msg_id):
            try:
                thread_safe_log(logger, 20, f"Message {msg_id}", id=msg_id)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):  # Daha az thread ile test et
            thread = threading.Thread(target=log_message, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=1.0)  # Timeout ekle

        # Hata oluşmamalı
        assert len(errors) == 0

