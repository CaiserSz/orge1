"""
Event Detector Unit Tests
Created: 2025-12-09 23:00:00
Last Modified: 2025-12-22 06:29:15
Version: 1.0.1
Description: Event Detection modülü için unit testler
"""

import sys
import time
import threading
from unittest.mock import Mock
from pathlib import Path

import pytest

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import EventDetector, EventType, ESP32State
from api.config import config


class TestEventDetector:
    """Event Detector unit testleri"""

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

    def _transition(self, from_state: int, to_state: int) -> None:
        self.detector._check_state_transition(from_state, {"STATE": from_state})
        self.detector._check_state_transition(to_state, {"STATE": to_state})

    @pytest.mark.parametrize(
        ("from_state", "to_state", "expected_event"),
        [
            (
                ESP32State.IDLE.value,
                ESP32State.CABLE_DETECT.value,
                EventType.CABLE_CONNECTED,
            ),
            (
                ESP32State.CABLE_DETECT.value,
                ESP32State.EV_CONNECTED.value,
                EventType.EV_CONNECTED,
            ),
            (
                ESP32State.EV_CONNECTED.value,
                ESP32State.READY.value,
                EventType.CHARGE_READY,
            ),
            (
                ESP32State.READY.value,
                ESP32State.CHARGING.value,
                EventType.CHARGE_STARTED,
            ),
            (
                ESP32State.CHARGING.value,
                ESP32State.PAUSED.value,
                EventType.CHARGE_PAUSED,
            ),
            (
                ESP32State.CHARGING.value,
                ESP32State.STOPPED.value,
                EventType.CHARGE_STOPPED,
            ),
            (
                ESP32State.PAUSED.value,
                ESP32State.STOPPED.value,
                EventType.CHARGE_STOPPED,
            ),
            (
                ESP32State.CABLE_DETECT.value,
                ESP32State.IDLE.value,
                EventType.CABLE_DISCONNECTED,
            ),
            (
                ESP32State.EV_CONNECTED.value,
                ESP32State.IDLE.value,
                EventType.CABLE_DISCONNECTED,
            ),
            (
                ESP32State.CHARGING.value,
                ESP32State.FAULT_HARD.value,
                EventType.FAULT_DETECTED,
            ),
            (ESP32State.READY.value, ESP32State.IDLE.value, EventType.STATE_CHANGED),
        ],
    )
    def test_transition_events(
        self, from_state: int, to_state: int, expected_event: EventType
    ):
        self._transition(from_state, to_state)
        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == expected_event
        assert event_data["from_state"] == from_state
        assert event_data["to_state"] == to_state

    def test_no_event_on_same_state(self):
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )
        assert len(self.received_events) == 0

    def test_resume_candidate_suppressed_when_power_below_threshold(self, monkeypatch):
        """
        PAUSED -> CHARGING transition, meter power eşiği altında kalıyorsa
        CHARGE_STARTED (resume) event'i üretilmemeli.
        """
        # Config'i hızlı test için küçült
        config.RESUME_VALIDATION_ENABLED = True
        config.RESUME_MIN_POWER_KW = 5.0
        config.RESUME_DEBOUNCE_SECONDS = 0.05
        config.RESUME_SAMPLE_INTERVAL_SECONDS = 0.01
        config.RESUME_REQUIRED_CONSECUTIVE_SAMPLES = 2
        config.RESUME_SUPPRESS_COOLDOWN_SECONDS = 0.0

        class _Reading:
            is_valid = True
            power_kw = 0.1

        class _Meter:
            def is_connected(self):
                return True

            def connect(self):
                return True

            def read_all(self):
                return _Reading()

        import api.meter as meter_module

        monkeypatch.setattr(meter_module, "get_meter", lambda: _Meter())

        # İlk state: PAUSED
        self.detector._check_state_transition(
            ESP32State.PAUSED.value, {"STATE": ESP32State.PAUSED.value}
        )

        # Resume adayı: CHARGING
        self.mock_bridge.get_status = Mock(
            return_value={"STATE": ESP32State.CHARGING.value}
        )
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )

        # Doğrulama thread'inin bitmesini bekle
        time.sleep(0.15)

        # Resume event'i üretilmemeli
        assert len(self.received_events) == 0

    def test_resume_candidate_emits_charge_started_when_power_validated(
        self, monkeypatch
    ):
        """
        PAUSED -> CHARGING transition, meter power eşiği üstünde stabil kalıyorsa
        CHARGE_STARTED (resume) event'i üretilmeli.
        """
        config.RESUME_VALIDATION_ENABLED = True
        config.RESUME_MIN_POWER_KW = 1.0
        config.RESUME_DEBOUNCE_SECONDS = 0.2
        config.RESUME_SAMPLE_INTERVAL_SECONDS = 0.01
        config.RESUME_REQUIRED_CONSECUTIVE_SAMPLES = 2
        config.RESUME_SUPPRESS_COOLDOWN_SECONDS = 0.0

        class _Reading:
            is_valid = True
            power_kw = 2.5

        class _Meter:
            def is_connected(self):
                return True

            def connect(self):
                return True

            def read_all(self):
                return _Reading()

        import api.meter as meter_module

        monkeypatch.setattr(meter_module, "get_meter", lambda: _Meter())

        # İlk state: PAUSED
        self.detector._check_state_transition(
            ESP32State.PAUSED.value, {"STATE": ESP32State.PAUSED.value}
        )

        # Resume adayı: CHARGING
        self.mock_bridge.get_status = Mock(
            return_value={"STATE": ESP32State.CHARGING.value}
        )
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )

        # Doğrulama thread'inin bitmesini bekle
        time.sleep(0.15)

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.CHARGE_STARTED
        assert event_data["from_state"] == ESP32State.PAUSED.value
        assert event_data["to_state"] == ESP32State.CHARGING.value

    def test_get_state_names(self):
        cases = [
            (ESP32State.IDLE.value, "IDLE"),
            (ESP32State.CABLE_DETECT.value, "CABLE_DETECT"),
            (ESP32State.EV_CONNECTED.value, "EV_CONNECTED"),
            (ESP32State.READY.value, "READY"),
            (ESP32State.CHARGING.value, "CHARGING"),
            (ESP32State.PAUSED.value, "PAUSED"),
            (ESP32State.STOPPED.value, "STOPPED"),
            (ESP32State.FAULT_HARD.value, "FAULT_HARD"),
            (99, "UNKNOWN_99"),
        ]
        for state, expected in cases:
            assert self.detector._get_state_name(state) == expected

    def test_get_current_state(self):
        """Mevcut state doğru döndürülüyor mu?"""
        assert self.detector.get_current_state() is None

        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )
        assert self.detector.get_current_state() == ESP32State.CHARGING.value

    def test_get_previous_state(self):
        """Önceki state doğru döndürülüyor mu?"""
        assert self.detector.get_previous_state() is None

        self.detector._check_state_transition(
            ESP32State.READY.value, {"STATE": ESP32State.READY.value}
        )
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )
        assert self.detector.get_previous_state() == ESP32State.READY.value

    def test_callback_registration(self):
        """Callback kayıt ve kaldırma çalışıyor mu?"""
        callback1_called = []
        callback2_called = []

        def callback1(event_type, event_data):
            callback1_called.append(True)

        def callback2(event_type, event_data):
            callback2_called.append(True)

        self.detector.register_callback(callback1)
        self.detector.register_callback(callback2)

        # Event oluştur
        self.detector._check_state_transition(
            ESP32State.IDLE.value, {"STATE": ESP32State.IDLE.value}
        )
        self.detector._check_state_transition(
            ESP32State.CABLE_DETECT.value, {"STATE": ESP32State.CABLE_DETECT.value}
        )

        # Her iki callback de çağrılmalı
        assert len(callback1_called) == 1
        assert len(callback2_called) == 1

        # Callback kaldır
        self.detector.unregister_callback(callback1)
        self.detector._check_state_transition(
            ESP32State.CABLE_DETECT.value, {"STATE": ESP32State.CABLE_DETECT.value}
        )
        self.detector._check_state_transition(
            ESP32State.EV_CONNECTED.value, {"STATE": ESP32State.EV_CONNECTED.value}
        )

        # Sadece callback2 çağrılmalı
        assert len(callback1_called) == 1
        assert len(callback2_called) == 2

    def test_thread_safety(self):
        """Thread-safe çalışıyor mu?"""
        events_received = []
        lock = threading.Lock()

        def event_callback(event_type, event_data):
            with lock:
                events_received.append((event_type, event_data))

        self.detector.register_callback(event_callback)

        def transition_thread(state_from, state_to, iterations=5):
            # Her thread kendi state transition'ını yapar
            for i in range(iterations):
                self.detector._check_state_transition(state_from, {"STATE": state_from})
                time.sleep(0.001)  # Kısa bekleme
                self.detector._check_state_transition(state_to, {"STATE": state_to})
                time.sleep(0.001)  # Kısa bekleme

        # İki thread paralel çalıştır
        thread1 = threading.Thread(
            target=transition_thread,
            args=(ESP32State.IDLE.value, ESP32State.CABLE_DETECT.value, 5),
        )
        thread2 = threading.Thread(
            target=transition_thread,
            args=(ESP32State.CHARGING.value, ESP32State.PAUSED.value, 5),
        )

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Her thread 5 event oluşturmalı (toplam 10)
        # Ancak thread'ler birbirini etkileyebilir, bu yüzden en az 5 event olmalı
        assert (
            len(events_received) >= 5
        ), f"Beklenen: en az 5, Alınan: {len(events_received)}"

        # Thread safety kontrolü: event'ler düzgün kaydedilmiş mi?
        # Her event'in timestamp'i olmalı
        for event_type, event_data in events_received:
            assert "timestamp" in event_data
            assert "from_state" in event_data
            assert "to_state" in event_data

    def test_monitoring_start_stop(self):
        """Monitoring başlatma ve durdurma çalışıyor mu?"""
        assert not self.detector.is_monitoring

        self.detector.start_monitoring()
        assert self.detector.is_monitoring

        time.sleep(0.1)  # Kısa bir bekleme

        self.detector.stop_monitoring()
        assert not self.detector.is_monitoring
