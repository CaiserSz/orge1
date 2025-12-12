"""
Event Detector Integration Tests
Created: 2025-12-13 02:35:00
Last Modified: 2025-12-13 02:35:00
Version: 1.0.0
Description: EventDetector entegrasyon testleri.
"""

from datetime import datetime
from unittest.mock import Mock

from api.event_detector import ESP32State, EventDetector, EventType


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
