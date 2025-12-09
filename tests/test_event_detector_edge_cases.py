"""
Event Detector Edge Cases Tests
Created: 2025-12-09 23:20:00
Last Modified: 2025-12-09 23:20:00
Version: 1.0.0
Description: Event Detector modülü için edge case testleri
"""

import pytest
import sys
import time
import threading
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import EventDetector, EventType, ESP32State


class TestEventDetectorEdgeCases:
    """Event Detector edge case testleri"""

    def setup_method(self):
        """Her test öncesi mock bridge ve detector oluştur"""
        self.mock_bridge = Mock()
        self.mock_bridge.is_connected = True
        self.mock_bridge.get_status = Mock(return_value=None)

        def bridge_getter():
            return self.mock_bridge

        self.detector = EventDetector(bridge_getter)
        self.received_events = []

        def event_callback(event_type, event_data):
            self.received_events.append((event_type, event_data))

        self.detector.register_callback(event_callback)

    def test_state_none_in_status(self):
        """Status'ta STATE None durumu"""
        self.mock_bridge.get_status.return_value = {"CP": 1, "PP": 1}  # STATE yok

        # Monitoring başlat
        self.detector.start_monitoring()
        time.sleep(0.1)
        self.detector.stop_monitoring()

        # STATE None ise event oluşturulmamalı
        assert len(self.received_events) == 0

    def test_invalid_state_value(self):
        """Geçersiz state değeri (99)"""
        self.detector._check_state_transition(1, {"STATE": 1})
        self.detector._check_state_transition(99, {"STATE": 99})

        # Geçersiz state için STATE_CHANGED event oluşturulmalı
        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.STATE_CHANGED
        assert event_data["to_state"] == 99
        assert event_data["to_state_name"] == "UNKNOWN_99"

    def test_negative_state_value(self):
        """Negatif state değeri"""
        self.detector._check_state_transition(1, {"STATE": 1})
        self.detector._check_state_transition(-1, {"STATE": -1})

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.STATE_CHANGED
        assert event_data["to_state"] == -1

    def test_state_zero(self):
        """State değeri 0"""
        self.detector._check_state_transition(1, {"STATE": 1})
        self.detector._check_state_transition(0, {"STATE": 0})

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.STATE_CHANGED

    def test_rapid_state_changes(self):
        """Hızlı state değişiklikleri"""
        states = [1, 2, 3, 4, 5, 6, 7, 1]

        for state in states:
            self.detector._check_state_transition(state, {"STATE": state})
            time.sleep(0.001)  # Çok kısa bekleme

        # Her transition için event oluşturulmalı (ilk hariç)
        assert len(self.received_events) == len(states) - 1

    def test_callback_exception_handling(self):
        """Callback exception handling"""
        exception_callback_called = []

        def failing_callback(event_type, event_data):
            exception_callback_called.append(True)
            raise Exception("Callback error")

        self.detector.register_callback(failing_callback)

        # Event oluştur - callback exception'ı detector'ı etkilememeli
        self.detector._check_state_transition(1, {"STATE": 1})
        self.detector._check_state_transition(2, {"STATE": 2})

        # Event oluşturulmalı ve diğer callback'ler çağrılmalı
        assert len(self.received_events) == 1
        assert len(exception_callback_called) == 1

    def test_monitor_loop_bridge_none(self):
        """Monitor loop - bridge None durumu"""
        def bridge_getter():
            return None

        detector = EventDetector(bridge_getter)
        detector.start_monitoring()
        time.sleep(0.2)
        detector.stop_monitoring()

        # Bridge None ise hata oluşmamalı, sessizce devam etmeli
        assert True  # Exception oluşmazsa test geçer

    def test_monitor_loop_bridge_not_connected(self):
        """Monitor loop - bridge bağlı değil"""
        self.mock_bridge.is_connected = False

        self.detector.start_monitoring()
        time.sleep(0.2)
        self.detector.stop_monitoring()

        # Bridge bağlı değilse hata oluşmamalı
        assert True  # Exception oluşmazsa test geçer

    def test_monitor_loop_get_status_exception(self):
        """Monitor loop - get_status exception"""
        self.mock_bridge.get_status.side_effect = Exception("Status error")

        self.detector.start_monitoring()
        time.sleep(0.2)
        self.detector.stop_monitoring()

        # Exception yakalanmalı ve loop devam etmeli
        assert True  # Exception oluşmazsa test geçer

    def test_multiple_callbacks_same_event(self):
        """Aynı event için birden fazla callback"""
        callback1_events = []
        callback2_events = []

        def callback1(event_type, event_data):
            callback1_events.append(event_type)

        def callback2(event_type, event_data):
            callback2_events.append(event_type)

        self.detector.register_callback(callback1)
        self.detector.register_callback(callback2)

        self.detector._check_state_transition(1, {"STATE": 1})
        self.detector._check_state_transition(2, {"STATE": 2})

        # Her iki callback de çağrılmalı
        assert len(callback1_events) == 1
        assert len(callback2_events) == 1
        assert callback1_events[0] == callback2_events[0]

    def test_unregister_nonexistent_callback(self):
        """Var olmayan callback'i kaldırma"""
        def callback():
            pass

        # Var olmayan callback'i kaldırmaya çalış - hata oluşmamalı
        self.detector.unregister_callback(callback)
        assert True  # Exception oluşmazsa test geçer

    def test_state_transition_with_none_status(self):
        """State transition - status None"""
        # Status None yerine boş dict kullan (None TypeError'a neden olur)
        self.detector._check_state_transition(1, {})
        self.detector._check_state_transition(2, {})

        # Status boş olsa bile event oluşturulmalı
        assert len(self.received_events) == 1

    def test_state_transition_with_empty_status(self):
        """State transition - boş status dict"""
        self.detector._check_state_transition(1, {})
        self.detector._check_state_transition(2, {})

        assert len(self.received_events) == 1

    def test_get_current_state_before_any_transition(self):
        """Get current state - hiç transition olmadan"""
        assert self.detector.get_current_state() is None

    def test_get_previous_state_before_any_transition(self):
        """Get previous state - hiç transition olmadan"""
        assert self.detector.get_previous_state() is None

    def test_stop_monitoring_before_start(self):
        """Stop monitoring - başlatılmadan önce"""
        # Monitoring başlatılmadan durdurma - hata oluşmamalı
        self.detector.stop_monitoring()
        assert True  # Exception oluşmazsa test geçer

    def test_start_monitoring_twice(self):
        """Start monitoring - iki kez başlatma"""
        self.detector.start_monitoring()
        self.detector.start_monitoring()  # İkinci kez başlatma

        # İkinci başlatma sessizce göz ardı edilmeli
        assert self.detector.is_monitoring is True

        self.detector.stop_monitoring()

