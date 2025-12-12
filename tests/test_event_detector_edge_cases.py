"""
Event Detector Edge Case Tests
Created: 2025-12-10 01:40:00
Last Modified: 2025-12-10 01:40:00
Version: 1.0.0
Description: Event Detector callback, state name, and singleton tests
"""

import sys
import threading
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import EventDetector, get_event_detector


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
            8: "FAULT_HARD",
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
        # Firmware mapping: 0 -> HARDFAULT_END
        assert name == "HARDFAULT_END"

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
