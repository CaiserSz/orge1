"""
Unit and Edge Case Tests for Charge, Status, and Current APIs
Created: 2025-12-10 17:30:00
Last Modified: 2025-12-12 03:30:00
Version: 1.0.1
Description: Comprehensive unit and edge case tests for:
- POST /api/charge/start
- POST /api/charge/stop
- GET /api/status
- POST /api/maxcurrent
"""

import os
from datetime import datetime, timedelta

from api.event_detector import ESP32State


def _ts() -> str:
    return datetime.now().isoformat()


def _status(state: ESP32State | int, **extra):
    if isinstance(state, ESP32State):
        payload = {"STATE": state.value, "STATE_NAME": state.name}
    else:
        payload = {"STATE": state}
    payload.setdefault("MAX", 16)
    payload.setdefault("timestamp", _ts())
    payload.update(extra)
    return payload


class TestChargeStart:
    def test_charge_start_success_ev_connected(
        self, client, mock_esp32_bridge, test_headers
    ):
        mock_esp32_bridge.get_status.return_value = _status(ESP32State.EV_CONNECTED)
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_esp32_bridge.send_authorization.assert_called_once()

    def test_charge_start_missing_api_key(self, client, mock_esp32_bridge):
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers={"X-API-Key": ""},
        )
        assert response.status_code == 401

    def test_charge_start_invalid_json(self, client, mock_esp32_bridge, test_headers):
        response = client.post(
            "/api/charge/start",
            data="invalid json",
            headers={**test_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_charge_start_esp32_disconnected(
        self, client, mock_esp32_bridge, test_headers
    ):
        mock_esp32_bridge.is_connected = False
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )
        assert response.status_code == 503

    def test_charge_start_no_status_data(self, client, mock_esp32_bridge, test_headers):
        mock_esp32_bridge.get_status.return_value = None
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )
        assert response.status_code == 503

    def test_charge_start_all_states(self, client, mock_esp32_bridge, test_headers):
        invalid_states = [
            ESP32State.HARDFAULT_END,
            ESP32State.IDLE,
            ESP32State.CABLE_DETECT,
            ESP32State.READY,
            ESP32State.CHARGING,
            ESP32State.PAUSED,
            ESP32State.STOPPED,
            ESP32State.FAULT_HARD,
        ]

        for state in invalid_states:
            mock_esp32_bridge.get_status.return_value = _status(state)
            response = client.post(
                "/api/charge/start",
                json={"user_id": "test-user-123"},
                headers=test_headers,
            )
            assert response.status_code in [400, 503], f"State {state.name} should fail"

        mock_esp32_bridge.get_status.return_value = _status(ESP32State.EV_CONNECTED)
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )
        assert response.status_code == 200


class TestChargeStop:
    def test_charge_stop_success(self, client, mock_esp32_bridge, test_headers):
        response = client.post(
            "/api/charge/stop",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_esp32_bridge.send_charge_stop.assert_called_once()

    def test_charge_stop_esp32_disconnected(
        self, client, mock_esp32_bridge, test_headers
    ):
        mock_esp32_bridge.is_connected = False
        response = client.post(
            "/api/charge/stop",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )
        assert response.status_code == 503

    def test_charge_stop_command_failure(self, client, mock_esp32_bridge, test_headers):
        mock_esp32_bridge.send_charge_stop.return_value = False
        response = client.post(
            "/api/charge/stop",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )
        assert response.status_code == 500

    def test_charge_stop_missing_api_key(self, client, mock_esp32_bridge):
        response = client.post(
            "/api/charge/stop",
            json={"user_id": "test-user-123"},
            headers={"X-API-Key": ""},
        )
        assert response.status_code == 401


class TestStatus:
    def test_status_success(self, client, mock_esp32_bridge):
        mock_esp32_bridge.get_status.return_value = _status(ESP32State.IDLE)
        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["data"]["STATE"] == ESP32State.IDLE.value

    def test_status_esp32_disconnected(self, client, mock_esp32_bridge):
        mock_esp32_bridge.is_connected = False
        response = client.get("/api/status")
        assert response.status_code == 503

    def test_status_stale_data(self, client, mock_esp32_bridge):
        stale_timestamp = (datetime.now() - timedelta(seconds=15)).isoformat()
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
            "timestamp": stale_timestamp,
        }
        fresh_data = _status(ESP32State.IDLE)
        mock_esp32_bridge.get_status_sync.side_effect = lambda timeout=None: fresh_data

        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_status_timeout(self, client, mock_esp32_bridge):
        mock_esp32_bridge.get_status.return_value = None
        mock_esp32_bridge.get_status_sync.side_effect = lambda timeout=None: None

        response = client.get("/api/status")
        assert response.status_code == 504

    def test_status_all_states(self, client, mock_esp32_bridge):
        for state in ESP32State:
            mock_esp32_bridge.get_status.return_value = _status(state)
            response = client.get("/api/status")
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["STATE"] == state.value


class TestMaxCurrent:
    def test_set_current_success_idle(self, client, mock_esp32_bridge, test_headers):
        mock_esp32_bridge.get_status.return_value = _status(ESP32State.IDLE)
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20},
            headers=test_headers,
        )
        assert response.status_code == 200
        mock_esp32_bridge.send_current_set.assert_called_once_with(20)

    def test_set_current_success_ev_connected(
        self, client, mock_esp32_bridge, test_headers
    ):
        mock_esp32_bridge.get_status.return_value = _status(ESP32State.EV_CONNECTED)
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 25},
            headers=test_headers,
        )
        assert response.status_code == 200

    def test_set_current_invalid_states(self, client, mock_esp32_bridge, test_headers):
        for state in [ESP32State.CHARGING, ESP32State.PAUSED, ESP32State.STOPPED]:
            mock_esp32_bridge.get_status.return_value = _status(state)
            response = client.post(
                "/api/maxcurrent",
                json={"amperage": 20},
                headers=test_headers,
            )
            assert response.status_code in [400, 503]

    def test_set_current_boundary_values(self, client, mock_esp32_bridge, test_headers):
        mock_esp32_bridge.get_status.return_value = _status(ESP32State.IDLE)

        for amperage, expected in [(6, 200), (32, 200), (5, 422), (33, 422)]:
            response = client.post(
                "/api/maxcurrent",
                json={"amperage": amperage},
                headers=test_headers,
            )
            assert response.status_code == expected

    def test_set_current_missing_field(self, client, mock_esp32_bridge, test_headers):
        response = client.post("/api/maxcurrent", json={}, headers=test_headers)
        assert response.status_code == 422

    def test_set_current_non_integer(self, client, mock_esp32_bridge, test_headers):
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20.5},
            headers=test_headers,
        )
        assert response.status_code == 422

    def test_set_current_esp32_disconnected(
        self, client, mock_esp32_bridge, test_headers
    ):
        mock_esp32_bridge.is_connected = False
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20},
            headers=test_headers,
        )
        assert response.status_code == 503

    def test_set_current_all_valid_states(
        self, client, mock_esp32_bridge, test_headers
    ):
        for state in [ESP32State.IDLE, ESP32State.EV_CONNECTED, ESP32State.READY]:
            mock_esp32_bridge.get_status.return_value = _status(state)
            response = client.post(
                "/api/maxcurrent",
                json={"amperage": 20},
                headers=test_headers,
            )
            assert response.status_code == 200


class TestEdgeCases:
    def test_concurrent_charge_start(self, client, mock_esp32_bridge, test_headers):
        mock_esp32_bridge.get_status.return_value = _status(ESP32State.EV_CONNECTED)

        response1 = client.post(
            "/api/charge/start",
            json={"user_id": "user-1"},
            headers=test_headers,
        )
        response2 = client.post(
            "/api/charge/start",
            json={"user_id": "user-2"},
            headers=test_headers,
        )

        assert response1.status_code == 200
        assert response2.status_code in [200, 400, 503, 429]

    def test_status_caching(self, client, mock_esp32_bridge):
        mock_esp32_bridge.get_status.return_value = _status(ESP32State.IDLE)

        from api.cache import get_cache_backend

        os.environ["PYTEST_ENABLE_CACHE"] = "1"
        try:
            get_cache_backend().clear()
            response1 = client.get("/api/status")
            response2 = client.get("/api/status")
            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response1.json() == response2.json()
        finally:
            os.environ.pop("PYTEST_ENABLE_CACHE", None)
            get_cache_backend().clear()
