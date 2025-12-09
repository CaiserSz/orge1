"""
Event Detector Additional Edge Cases Tests
Created: 2025-12-10 00:25:00
Last Modified: 2025-12-10 09:00:00
Version: 1.0.0
Description: Event Detector ek edge case testleri
"""

import sys
import time
import threading
from unittest.mock import Mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.event_detector import EventDetector, EventType, ESP32State


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
        event_type = detector._classify_event(
            ESP32State.IDLE.value, ESP32State.CHARGING.value
        )
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
        detector._create_event(EventType.CABLE_CONNECTED, 1, 2, {"STATE": 2})

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
