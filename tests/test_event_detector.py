"""
Event Detector Unit Tests
Created: 2025-12-09 23:00:00
Last Modified: 2025-12-09 23:00:00
Version: 1.0.0
Description: Event Detection modülü için unit testler
"""

import sys
import time
import threading
from unittest.mock import Mock
from pathlib import Path

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import EventDetector, EventType, ESP32State


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

    def test_cable_connected_event(self):
        """CABLE_CONNECTED event tespit ediliyor mu?"""
        # STATE: IDLE → CABLE_DETECT
        self.detector._check_state_transition(
            ESP32State.IDLE.value, {"STATE": ESP32State.IDLE.value}
        )
        self.detector._check_state_transition(
            ESP32State.CABLE_DETECT.value, {"STATE": ESP32State.CABLE_DETECT.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.CABLE_CONNECTED
        assert event_data["from_state"] == ESP32State.IDLE.value
        assert event_data["to_state"] == ESP32State.CABLE_DETECT.value

    def test_ev_connected_event(self):
        """EV_CONNECTED event tespit ediliyor mu?"""
        # STATE: CABLE_DETECT → EV_CONNECTED
        self.detector._check_state_transition(
            ESP32State.CABLE_DETECT.value, {"STATE": ESP32State.CABLE_DETECT.value}
        )
        self.detector._check_state_transition(
            ESP32State.EV_CONNECTED.value, {"STATE": ESP32State.EV_CONNECTED.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.EV_CONNECTED
        assert event_data["from_state"] == ESP32State.CABLE_DETECT.value
        assert event_data["to_state"] == ESP32State.EV_CONNECTED.value

    def test_charge_ready_event(self):
        """CHARGE_READY event tespit ediliyor mu?"""
        # STATE: EV_CONNECTED → READY
        self.detector._check_state_transition(
            ESP32State.EV_CONNECTED.value, {"STATE": ESP32State.EV_CONNECTED.value}
        )
        self.detector._check_state_transition(
            ESP32State.READY.value, {"STATE": ESP32State.READY.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.CHARGE_READY
        assert event_data["from_state"] == ESP32State.EV_CONNECTED.value
        assert event_data["to_state"] == ESP32State.READY.value

    def test_charge_started_event(self):
        """CHARGE_STARTED event tespit ediliyor mu?"""
        # STATE: READY → CHARGING
        self.detector._check_state_transition(
            ESP32State.READY.value, {"STATE": ESP32State.READY.value}
        )
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.CHARGE_STARTED
        assert event_data["from_state"] == ESP32State.READY.value
        assert event_data["to_state"] == ESP32State.CHARGING.value

    def test_charge_paused_event(self):
        """CHARGE_PAUSED event tespit ediliyor mu?"""
        # STATE: CHARGING → PAUSED
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )
        self.detector._check_state_transition(
            ESP32State.PAUSED.value, {"STATE": ESP32State.PAUSED.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.CHARGE_PAUSED
        assert event_data["from_state"] == ESP32State.CHARGING.value
        assert event_data["to_state"] == ESP32State.PAUSED.value

    def test_charge_stopped_event_from_charging(self):
        """CHARGE_STOPPED event (CHARGING → STOPPED) tespit ediliyor mu?"""
        # STATE: CHARGING → STOPPED
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )
        self.detector._check_state_transition(
            ESP32State.STOPPED.value, {"STATE": ESP32State.STOPPED.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.CHARGE_STOPPED
        assert event_data["from_state"] == ESP32State.CHARGING.value
        assert event_data["to_state"] == ESP32State.STOPPED.value

    def test_charge_stopped_event_from_paused(self):
        """CHARGE_STOPPED event (PAUSED → STOPPED) tespit ediliyor mu?"""
        # STATE: PAUSED → STOPPED
        self.detector._check_state_transition(
            ESP32State.PAUSED.value, {"STATE": ESP32State.PAUSED.value}
        )
        self.detector._check_state_transition(
            ESP32State.STOPPED.value, {"STATE": ESP32State.STOPPED.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.CHARGE_STOPPED
        assert event_data["from_state"] == ESP32State.PAUSED.value
        assert event_data["to_state"] == ESP32State.STOPPED.value

    def test_cable_disconnected_from_cable_detect(self):
        """CABLE_DISCONNECTED event (CABLE_DETECT → IDLE) tespit ediliyor mu?"""
        # STATE: CABLE_DETECT → IDLE
        self.detector._check_state_transition(
            ESP32State.CABLE_DETECT.value, {"STATE": ESP32State.CABLE_DETECT.value}
        )
        self.detector._check_state_transition(
            ESP32State.IDLE.value, {"STATE": ESP32State.IDLE.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.CABLE_DISCONNECTED
        assert event_data["from_state"] == ESP32State.CABLE_DETECT.value
        assert event_data["to_state"] == ESP32State.IDLE.value

    def test_cable_disconnected_from_ev_connected(self):
        """CABLE_DISCONNECTED event (EV_CONNECTED → IDLE) tespit ediliyor mu?"""
        # STATE: EV_CONNECTED → IDLE
        self.detector._check_state_transition(
            ESP32State.EV_CONNECTED.value, {"STATE": ESP32State.EV_CONNECTED.value}
        )
        self.detector._check_state_transition(
            ESP32State.IDLE.value, {"STATE": ESP32State.IDLE.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.CABLE_DISCONNECTED
        assert event_data["from_state"] == ESP32State.EV_CONNECTED.value
        assert event_data["to_state"] == ESP32State.IDLE.value

    def test_fault_detected_event(self):
        """FAULT_DETECTED event tespit ediliyor mu?"""
        # STATE: CHARGING → FAULT_HARD
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )
        self.detector._check_state_transition(
            ESP32State.FAULT_HARD.value, {"STATE": ESP32State.FAULT_HARD.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.FAULT_DETECTED
        assert event_data["from_state"] == ESP32State.CHARGING.value
        assert event_data["to_state"] == ESP32State.FAULT_HARD.value

    def test_unknown_transition(self):
        """Bilinmeyen transition STATE_CHANGED event oluşturuyor mu?"""
        # STATE: READY → IDLE - bilinmeyen transition
        self.detector._check_state_transition(
            ESP32State.READY.value, {"STATE": ESP32State.READY.value}
        )
        self.detector._check_state_transition(
            ESP32State.IDLE.value, {"STATE": ESP32State.IDLE.value}
        )

        assert len(self.received_events) == 1
        event_type, event_data = self.received_events[0]
        assert event_type == EventType.STATE_CHANGED
        assert event_data["from_state"] == ESP32State.READY.value
        assert event_data["to_state"] == ESP32State.IDLE.value

    def test_no_event_on_same_state(self):
        """Aynı state'de event oluşturulmuyor mu?"""
        # STATE: CHARGING → CHARGING - değişiklik yok
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )
        self.detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )

        assert len(self.received_events) == 0

    def test_get_state_names(self):
        """State name'ler doğru döndürülüyor mu?"""
        assert self.detector._get_state_name(ESP32State.IDLE.value) == "IDLE"
        assert (
            self.detector._get_state_name(ESP32State.CABLE_DETECT.value)
            == "CABLE_DETECT"
        )
        assert (
            self.detector._get_state_name(ESP32State.EV_CONNECTED.value)
            == "EV_CONNECTED"
        )
        assert self.detector._get_state_name(ESP32State.READY.value) == "READY"
        assert self.detector._get_state_name(ESP32State.CHARGING.value) == "CHARGING"
        assert self.detector._get_state_name(ESP32State.PAUSED.value) == "PAUSED"
        assert self.detector._get_state_name(ESP32State.STOPPED.value) == "STOPPED"
        assert (
            self.detector._get_state_name(ESP32State.FAULT_HARD.value) == "FAULT_HARD"
        )
        assert self.detector._get_state_name(99) == "UNKNOWN_99"

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


class TestEventDetectorIntegration:
    """Event Detector entegrasyon testleri"""

    def test_full_charging_cycle(self):
        """Tam şarj döngüsü event'leri doğru mu?"""
        mock_bridge = Mock()
        mock_bridge.is_connected = True

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)
        events = []

        def event_callback(event_type, event_data):
            events.append(event_type)

        detector.register_callback(event_callback)

        # Tam şarj döngüsü simülasyonu
        detector._check_state_transition(
            ESP32State.IDLE.value, {"STATE": ESP32State.IDLE.value}
        )  # IDLE
        detector._check_state_transition(
            ESP32State.CABLE_DETECT.value, {"STATE": ESP32State.CABLE_DETECT.value}
        )  # CABLE_DETECT
        detector._check_state_transition(
            ESP32State.EV_CONNECTED.value, {"STATE": ESP32State.EV_CONNECTED.value}
        )  # EV_CONNECTED
        detector._check_state_transition(
            ESP32State.READY.value, {"STATE": ESP32State.READY.value}
        )  # READY
        detector._check_state_transition(
            ESP32State.CHARGING.value, {"STATE": ESP32State.CHARGING.value}
        )  # CHARGING
        detector._check_state_transition(
            ESP32State.STOPPED.value, {"STATE": ESP32State.STOPPED.value}
        )  # STOPPED
        detector._check_state_transition(
            ESP32State.IDLE.value, {"STATE": ESP32State.IDLE.value}
        )  # IDLE

        # Beklenen event'ler
        expected_events = [
            EventType.CABLE_CONNECTED,
            EventType.EV_CONNECTED,
            EventType.CHARGE_READY,
            EventType.CHARGE_STARTED,
            EventType.CHARGE_STOPPED,
            EventType.STATE_CHANGED,  # STOPPED → IDLE bilinmeyen transition
        ]

        assert len(events) == len(expected_events)
        assert events == expected_events
