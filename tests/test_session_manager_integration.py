"""
Session Manager Integration Tests
Created: 2025-12-13 02:32:00
Last Modified: 2025-12-13 02:32:00
Version: 1.0.0
Description: SessionManager singleton ve event detector entegrasyon testleri.
"""

from datetime import datetime
from unittest.mock import Mock

from api.event_detector import ESP32State, EventType
from api.session import SessionManager, SessionStatus, get_session_manager


class TestSessionManagerSingleton:
    """Session Manager singleton pattern testleri"""

    def test_singleton_pattern(self):
        """Singleton pattern testi"""
        manager1 = get_session_manager()
        manager2 = get_session_manager()

        assert manager1 is manager2


class TestSessionManagerIntegration:
    """Session Manager entegrasyon testleri"""

    def test_register_with_event_detector(self):
        """Event Detector'a kayıt testi"""
        manager = SessionManager()
        event_detector = Mock()
        event_detector.register_callback = Mock()

        manager.register_with_event_detector(event_detector)

        event_detector.register_callback.assert_called_once()
        # Callback'in manager._on_event olduğunu kontrol et
        callback = event_detector.register_callback.call_args[0][0]
        assert callable(callback)

    def test_event_detector_callback(self):
        """Event Detector callback entegrasyonu testi"""
        manager = SessionManager()
        event_detector = Mock()

        manager.register_with_event_detector(event_detector)

        # Callback'i al ve çağır
        callback = event_detector.register_callback.call_args[0][0]
        event_data = {"to_state": ESP32State.CHARGING.value}

        callback(EventType.CHARGE_STARTED, event_data)

        assert manager.current_session is not None
        assert manager.current_session.status == SessionStatus.ACTIVE
