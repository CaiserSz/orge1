"""
Mobile API Tests
Created: 2025-12-13 03:20:00
Last Modified: 2025-12-13 03:20:00
Version: 1.0.0
Description: Mobil şarj API uç noktaları için entegrasyon testleri.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))


class _DummyMeterReading:
    def __init__(self):
        self.timestamp = datetime.now(timezone.utc).timestamp()
        self.voltage_v = 231.0
        self.current_a = 32.0
        self.power_kw = 7.4
        self.power_w = 7400
        self.energy_kwh = 1542.6
        self.frequency_hz = 50.0
        self.power_factor = 0.98
        self.is_valid = True
        self.phase_values = {
            "voltage_v": {"L1": 231.0, "L2": 0.0, "L3": 0.0},
            "current_a": {"L1": 32.0, "L2": 0.0, "L3": 0.0},
            "power_kw": {"L1": 7.4, "L2": 0.0, "L3": 0.0, "total": 7.4},
        }
        self.totals = {"energy_kwh": 1542.6}


class _DummyMeter:
    def __init__(self):
        self._connected = True

    def is_connected(self):
        return self._connected

    def connect(self):
        self._connected = True
        return True

    def read_all(self):
        return _DummyMeterReading()


class _DummySessionManager:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self._sessions: List[Dict[str, Any]] = [
            {
                "session_id": "sess-001",
                "start_time": (now - timedelta(hours=1)).isoformat(),
                "end_time": (now - timedelta(minutes=10)).isoformat(),
                "status": "COMPLETED",
                "total_energy_kwh": 12.5,
                "events": [
                    {
                        "timestamp": (now - timedelta(minutes=50)).isoformat(),
                        "event_type": "CHARGE_STARTED",
                        "data": {"status": {"CURRENT": 16, "CPV": 4000}},
                    }
                ],
                "metadata": {"user_id": "user-1"},
            },
            {
                "session_id": "sess-002",
                "start_time": (now - timedelta(days=1)).isoformat(),
                "end_time": (now - timedelta(days=1, hours=-1)).isoformat(),
                "status": "COMPLETED",
                "total_energy_kwh": 6.0,
                "events": [],
                "metadata": {"user_id": "user-2"},
            },
        ]
        self._current_session = {
            "session_id": "sess-current",
            "start_time": (now - timedelta(minutes=30)).isoformat(),
            "status": "CHARGING",
            "metadata": {"user_id": "user-1"},
        }

    def get_current_session(self):
        return self._current_session

    def get_sessions(self, limit=100, offset=0, status=None, user_id=None):
        return self._sessions[:limit]

    def get_session(self, session_id: str):
        for session in self._sessions + [self._current_session]:
            if session.get("session_id") == session_id:
                return session
        return None


class _DummyAlert:
    def __init__(self):
        self.name = "LOW_VOLTAGE"
        self.severity = type("Severity", (), {"value": "warning"})()
        self.message = "L2 voltage below threshold"
        self.timestamp = datetime.now(timezone.utc)
        self.metadata = {"phase": "L2"}


class _DummyAlertManager:
    def get_active_alerts(self):
        return [_DummyAlert()]


@pytest.fixture(autouse=True)
def mobile_dependency_overrides(monkeypatch):
    station_info = {
        "station_id": "station-123",
        "name": "Demo Station",
        "address": "Istanbul",
        "latitude": 41.01,
        "longitude": 28.97,
        "max_power_kw": 22,
        "max_current_amp": 32,
        "price_per_kwh": 8.5,
        "currency": "TRY",
    }

    dummy_meter = _DummyMeter()
    dummy_sessions = _DummySessionManager()
    dummy_alert_manager = _DummyAlertManager()

    monkeypatch.setattr("api.routers.mobile.get_meter", lambda: dummy_meter)
    monkeypatch.setattr(
        "api.routers.mobile.get_station_info", lambda: dict(station_info)
    )
    monkeypatch.setattr(
        "api.routers.mobile.get_session_manager", lambda: dummy_sessions
    )
    monkeypatch.setattr(
        "api.routers.mobile.get_alert_manager", lambda: dummy_alert_manager
    )
    yield


def test_mobile_current_endpoint_returns_combined_payload(client):
    response = client.get("/api/mobile/charging/current")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["device"]["station_id"] == "station-123"
    assert data["session"]["session_id"] == "sess-current"
    assert data["measurements"]["power_kw"]["total"] == pytest.approx(7.4)
    assert data["trend"]["sessions_today"] >= 0
    assert len(data["alerts"]) == 1


def test_mobile_session_detail_endpoint(client):
    response = client.get("/api/mobile/charging/sessions/sess-001")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["session_id"] == "sess-001"
    assert data["energy_kwh"] == pytest.approx(12.5)
    assert data["cost"]["per_kwh"] == 8.5


def test_mobile_session_list_filters_by_date(client):
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=2)).isoformat()
    response = client.get(
        "/api/mobile/charging/sessions", params={"from": start, "limit": 5}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    sessions = data["sessions"]
    # Sadece bugünkü oturum beklenir
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "sess-001"
