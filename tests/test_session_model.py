"""
Session Model Test Suite
Created: 2025-12-13 02:30:00
Last Modified: 2025-12-13 02:30:00
Version: 1.0.0
Description: ChargingSession veri modeline ait unit testler.
"""

from datetime import datetime

from api.event_detector import ESP32State, EventType
from api.session import ChargingSession, SessionStatus


class TestChargingSession:
    """ChargingSession sınıfı için testler"""

    def test_session_creation(self):
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
        session = ChargingSession("test-123", datetime.now(), ESP32State.CHARGING.value)
        event_data = {"test": "data"}

        session.add_event(EventType.CHARGE_PAUSED, event_data)

        assert len(session.events) == 1
        assert session.events[0]["event_type"] == EventType.CHARGE_PAUSED.value
        assert "timestamp" in session.events[0]
        assert session.events[0]["data"] == event_data

    def test_end_session(self):
        session = ChargingSession("test-123", datetime.now(), ESP32State.CHARGING.value)
        end_time = datetime.now()
        end_state = ESP32State.STOPPED.value

        session.end_session(end_time, end_state, SessionStatus.COMPLETED)

        assert session.end_time == end_time
        assert session.end_state == end_state
        assert session.status == SessionStatus.COMPLETED

    def test_to_dict(self):
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
        start_time = datetime.now()
        session = ChargingSession("test-123", start_time, ESP32State.CHARGING.value)
        end_time = datetime.now()
        session.end_session(end_time, ESP32State.STOPPED.value, SessionStatus.COMPLETED)
        session.add_event(EventType.CHARGE_STARTED, {"test": "data"})

        session_dict = session.to_dict()

        assert session_dict["end_time"] is not None
        assert session_dict["status"] == SessionStatus.COMPLETED.value
        assert "duration_seconds" in session_dict

    def test_session_with_metadata(self):
        session = ChargingSession("test-123", datetime.now(), ESP32State.CHARGING.value)
        session.metadata["user_id"] = "user-123"
        session.metadata["car_model"] = "Tesla Model 3"

        session_dict = session.to_dict()

        assert session_dict["metadata"]["user_id"] == "user-123"
        assert session_dict["metadata"]["car_model"] == "Tesla Model 3"

