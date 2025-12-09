"""
Session Manager Test Suite
Created: 2025-12-10 03:30:00
Last Modified: 2025-12-10 03:30:00
Version: 1.0.0
Description: Session Manager modülü için unit testler
"""

from datetime import datetime
from unittest.mock import Mock
from api.session import (
    SessionManager,
    ChargingSession,
    SessionStatus,
    get_session_manager,
)
from api.event_detector import EventType, ESP32State


class TestChargingSession:
    """ChargingSession sınıfı için testler"""

    def test_session_creation(self):
        """Session oluşturma testi"""
        session_id = "test-session-123"
        start_time = datetime.now()
        start_state = ESP32State.CHARGING.value

        session = ChargingSession(session_id, start_time, start_state)

        assert session.session_id == session_id
        assert session.start_time == start_time
        assert session.start_state == start_state
        assert session.status == SessionStatus.ACTIVE
        assert len(session.events) == 0
        assert session.end_time is None
        assert session.end_state is None

    def test_add_event(self):
        """Session'a event ekleme testi"""
        session = ChargingSession("test-123", datetime.now(), ESP32State.CHARGING.value)
        event_data = {"test": "data"}

        session.add_event(EventType.CHARGE_PAUSED, event_data)

        assert len(session.events) == 1
        assert session.events[0]["event_type"] == EventType.CHARGE_PAUSED.value
        assert "timestamp" in session.events[0]
        assert session.events[0]["data"] == event_data

    def test_end_session(self):
        """Session sonlandırma testi"""
        session = ChargingSession("test-123", datetime.now(), ESP32State.CHARGING.value)
        end_time = datetime.now()
        end_state = ESP32State.STOPPED.value

        session.end_session(end_time, end_state, SessionStatus.COMPLETED)

        assert session.end_time == end_time
        assert session.end_state == end_state
        assert session.status == SessionStatus.COMPLETED

    def test_to_dict(self):
        """Session dict dönüşümü testi"""
        session = ChargingSession("test-123", datetime.now(), ESP32State.CHARGING.value)
        session.add_event(EventType.CHARGE_STARTED, {"test": "data"})

        session_dict = session.to_dict()

        assert session_dict["session_id"] == "test-123"
        assert session_dict["status"] == SessionStatus.ACTIVE.value
        assert session_dict["event_count"] == 1
        assert session_dict["end_time"] is None
        assert "start_time" in session_dict
        assert "events" in session_dict

    def test_to_dict_with_end_time(self):
        """Bitiş zamanı olan session dict dönüşümü testi"""
        start_time = datetime.now()
        session = ChargingSession("test-123", start_time, ESP32State.CHARGING.value)
        end_time = datetime.now()
        session.end_session(end_time, ESP32State.STOPPED.value, SessionStatus.COMPLETED)

        session_dict = session.to_dict()

        assert session_dict["end_time"] == end_time.isoformat()
        assert session_dict["duration_seconds"] is not None
        assert session_dict["duration_seconds"] > 0


class TestSessionManager:
    """SessionManager sınıfı için testler"""

    def test_session_manager_creation(self):
        """Session Manager oluşturma testi"""
        manager = SessionManager()

        assert len(manager.sessions) == 0
        assert manager.current_session is None
        assert manager.max_sessions == 1000

    def test_start_session_on_charge_started(self):
        """CHARGE_STARTED event'inde session başlatma testi"""
        manager = SessionManager()
        event_data = {
            "to_state": ESP32State.CHARGING.value,
            "from_state": ESP32State.READY.value,
        }

        manager._on_event(EventType.CHARGE_STARTED, event_data)

        assert manager.current_session is not None
        assert manager.current_session.status == SessionStatus.ACTIVE
        assert len(manager.current_session.events) == 1
        assert (
            manager.current_session.events[0]["event_type"]
            == EventType.CHARGE_STARTED.value
        )

    def test_end_session_on_charge_stopped(self):
        """CHARGE_STOPPED event'inde session sonlandırma testi"""
        manager = SessionManager()

        # Önce session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        assert manager.current_session is not None

        # Sonra session sonlandır
        manager._on_event(
            EventType.CHARGE_STOPPED, {"to_state": ESP32State.STOPPED.value}
        )

        assert manager.current_session is None
        assert len(manager.sessions) == 1
        session = list(manager.sessions.values())[0]
        assert session.status == SessionStatus.COMPLETED
        assert session.end_time is not None

    def test_end_session_on_cable_disconnected(self):
        """CABLE_DISCONNECTED event'inde session sonlandırma testi"""
        manager = SessionManager()

        # Önce session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )

        # Sonra cable disconnected
        manager._on_event(
            EventType.CABLE_DISCONNECTED, {"to_state": ESP32State.IDLE.value}
        )

        assert manager.current_session is None
        session = list(manager.sessions.values())[0]
        assert session.status == SessionStatus.CANCELLED

    def test_fault_handling(self):
        """Fault durumu işleme testi"""
        manager = SessionManager()

        # Session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )

        # Fault event'i
        manager._on_event(
            EventType.FAULT_DETECTED, {"to_state": ESP32State.FAULT_HARD.value}
        )

        assert manager.current_session.status == SessionStatus.FAULTED
        assert (
            len(manager.current_session.events) == 2
        )  # CHARGE_STARTED + FAULT_DETECTED

    def test_add_event_to_active_session(self):
        """Aktif session'a event ekleme testi"""
        manager = SessionManager()

        # Session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )

        # Event ekle
        manager._on_event(
            EventType.CHARGE_PAUSED, {"to_state": ESP32State.PAUSED.value}
        )

        assert len(manager.current_session.events) == 2

    def test_new_session_cancels_previous(self):
        """Yeni session başlatıldığında önceki session'ı iptal etme testi"""
        manager = SessionManager()

        # İlk session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        first_session_id = manager.current_session.session_id

        # İkinci session başlat (önceki iptal edilmeli)
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        second_session_id = manager.current_session.session_id

        assert first_session_id != second_session_id
        assert len(manager.sessions) == 2

        # İlk session iptal edilmiş olmalı
        first_session = manager.sessions[first_session_id]
        assert first_session.status == SessionStatus.CANCELLED

    def test_get_current_session(self):
        """Aktif session alma testi"""
        manager = SessionManager()

        # Session yokken
        assert manager.get_current_session() is None

        # Session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )

        current = manager.get_current_session()
        assert current is not None
        assert current["status"] == SessionStatus.ACTIVE.value

    def test_get_session(self):
        """Belirli session alma testi"""
        manager = SessionManager()

        # Session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        session_id = manager.current_session.session_id

        # Session'ı al
        session = manager.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id

        # Olmayan session
        assert manager.get_session("non-existent") is None

    def test_get_sessions_with_pagination(self):
        """Session listesi pagination testi"""
        manager = SessionManager()

        # Birkaç session oluştur
        for i in range(5):
            manager._on_event(
                EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
            )
            manager._on_event(
                EventType.CHARGE_STOPPED, {"to_state": ESP32State.STOPPED.value}
            )

        # Pagination test
        sessions = manager.get_sessions(limit=2, offset=0)
        assert len(sessions) == 2

        sessions = manager.get_sessions(limit=2, offset=2)
        assert len(sessions) == 2

    def test_get_sessions_with_status_filter(self):
        """Status filtresi ile session listesi testi"""
        manager = SessionManager()

        # Completed session
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        manager._on_event(
            EventType.CHARGE_STOPPED, {"to_state": ESP32State.STOPPED.value}
        )

        # Cancelled session
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        manager._on_event(
            EventType.CABLE_DISCONNECTED, {"to_state": ESP32State.IDLE.value}
        )

        # Completed session'ları al
        completed = manager.get_sessions(status=SessionStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0]["status"] == SessionStatus.COMPLETED.value

        # Cancelled session'ları al
        cancelled = manager.get_sessions(status=SessionStatus.CANCELLED)
        assert len(cancelled) == 1
        assert cancelled[0]["status"] == SessionStatus.CANCELLED.value

    def test_get_session_count(self):
        """Session sayısı alma testi"""
        manager = SessionManager()

        assert manager.get_session_count() == 0

        # Birkaç session oluştur
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        manager._on_event(
            EventType.CHARGE_STOPPED, {"to_state": ESP32State.STOPPED.value}
        )

        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        manager._on_event(
            EventType.CABLE_DISCONNECTED, {"to_state": ESP32State.IDLE.value}
        )

        assert manager.get_session_count() == 2
        assert manager.get_session_count(SessionStatus.COMPLETED) == 1
        assert manager.get_session_count(SessionStatus.CANCELLED) == 1


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
