"""
Unit and Edge Case Tests for Charge, Status, and Current APIs
Created: 2025-12-10 17:30:00
Last Modified: 2025-12-10 17:30:00
Version: 1.0.0
Description: Comprehensive unit and edge case tests for:
- POST /api/charge/start
- POST /api/charge/stop
- GET /api/status
- POST /api/maxcurrent
"""

from datetime import datetime, timedelta
from api.event_detector import ESP32State

# conftest.py'den fixture'ları kullan: client, mock_esp32_bridge, test_headers


# ============================================================================
# POST /api/charge/start TESTS
# ============================================================================


class TestChargeStart:
    """Tests for POST /api/charge/start endpoint"""

    def test_charge_start_success_ev_connected(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test successful charge start when ESP32 is in EV_CONNECTED state"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "STATE_NAME": "EV_CONNECTED",
            "CP": 2,
            "CPV": 1847,
            "PP": 1,
            "PPV": 1566,
            "RL": 1,
            "LOCK": 1,
            "MOTOR": 0,
            "PWM": 0,
            "MAX": 16,
            "CABLE": 20,
            "AUTH": 0,
            "PB": 0,
            "STOP": 0,
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert (
            "komutu gönderildi" in data["message"]
            or "charge_start" in data["message"].lower()
        )
        mock_esp32_bridge.send_authorization.assert_called_once()

    def test_charge_start_without_user_id(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test charge start without user_id (should still work)"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "STATE_NAME": "EV_CONNECTED",
            "CP": 2,
            "CPV": 1847,
            "PP": 1,
            "PPV": 1566,
            "RL": 1,
            "LOCK": 1,
            "MOTOR": 0,
            "PWM": 0,
            "MAX": 16,
            "CABLE": 20,
            "AUTH": 0,
            "PB": 0,
            "STOP": 0,
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post("/api/charge/start", json={}, headers=test_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_charge_start_invalid_state_idle(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test charge start fails when ESP32 is in IDLE state"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )

        assert response.status_code in [400, 503]
        data = response.json()
        assert "detail" in data
        assert "IDLE" in data["detail"] or "başlatılamaz" in data["detail"]

    def test_charge_start_invalid_state_charging(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test charge start fails when already charging"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CHARGING.value,
            "STATE_NAME": "CHARGING",
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )

        assert response.status_code in [400, 503]
        data = response.json()
        assert "detail" in data
        assert "CHARGING" in data["detail"] or "aktif" in data["detail"]

    def test_charge_start_esp32_disconnected(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test charge start fails when ESP32 is disconnected"""
        mock_esp32_bridge.is_connected = False

        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )

        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert (
            "bağlantı" in data["detail"].lower()
            or "connection" in data["detail"].lower()
        )

    def test_charge_start_no_status_data(self, client, mock_esp32_bridge, test_headers):
        """Test charge start fails when status data is unavailable"""
        mock_esp32_bridge.get_status.return_value = None

        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )

        assert response.status_code == 503
        data = response.json()
        assert "detail" in data

    def test_charge_start_missing_api_key(self, client, mock_esp32_bridge):
        """Test charge start fails without API key"""
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
        )

        assert response.status_code == 401

    def test_charge_start_invalid_json(self, client, mock_esp32_bridge, test_headers):
        """Test charge start with invalid JSON"""
        response = client.post(
            "/api/charge/start",
            data="invalid json",
            headers={**test_headers, "Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_charge_start_all_states(self, client, mock_esp32_bridge, test_headers):
        """Test charge start with all possible ESP32 states"""
        invalid_states = [
            ESP32State.IDLE,
            ESP32State.CABLE_DETECT,
            ESP32State.READY,
            ESP32State.CHARGING,
            ESP32State.PAUSED,
            ESP32State.STOPPED,
            ESP32State.FAULT_HARD,
            ESP32State.HARDFAULT_END,
        ]

        for state in invalid_states:
            mock_esp32_bridge.get_status.return_value = {
                "STATE": state.value,
                "STATE_NAME": state.name,
                "timestamp": datetime.now().isoformat(),
            }

            response = client.post(
                "/api/charge/start",
                json={"user_id": "test-user-123"},
                headers=test_headers,
            )

            assert response.status_code in [400, 503], f"State {state.name} should fail"

        # Test valid state
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "STATE_NAME": "EV_CONNECTED",
            "CP": 2,
            "CPV": 1847,
            "PP": 1,
            "PPV": 1566,
            "RL": 1,
            "LOCK": 1,
            "MOTOR": 0,
            "PWM": 0,
            "MAX": 16,
            "CABLE": 20,
            "AUTH": 0,
            "PB": 0,
            "STOP": 0,
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/charge/start",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )

        assert response.status_code == 200


# ============================================================================
# POST /api/charge/stop TESTS
# ============================================================================


class TestChargeStop:
    """Tests for POST /api/charge/stop endpoint"""

    def test_charge_stop_success(self, client, mock_esp32_bridge, test_headers):
        """Test successful charge stop"""
        response = client.post(
            "/api/charge/stop",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stop" in data["message"].lower() or "durdurma" in data["message"]
        mock_esp32_bridge.send_charge_stop.assert_called_once()

    def test_charge_stop_without_user_id(self, client, mock_esp32_bridge, test_headers):
        """Test charge stop without user_id"""
        response = client.post("/api/charge/stop", json={}, headers=test_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_charge_stop_esp32_disconnected(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test charge stop fails when ESP32 is disconnected"""
        mock_esp32_bridge.is_connected = False

        response = client.post(
            "/api/charge/stop",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )

        assert response.status_code == 503
        data = response.json()
        assert "detail" in data

    def test_charge_stop_command_failure(self, client, mock_esp32_bridge, test_headers):
        """Test charge stop when ESP32 command fails"""
        mock_esp32_bridge.send_charge_stop.return_value = False

        response = client.post(
            "/api/charge/stop",
            json={"user_id": "test-user-123"},
            headers=test_headers,
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_charge_stop_missing_api_key(self, client, mock_esp32_bridge):
        """Test charge stop fails without API key"""
        response = client.post(
            "/api/charge/stop",
            json={"user_id": "test-user-123"},
        )

        assert response.status_code == 401


# ============================================================================
# GET /api/status TESTS
# ============================================================================


class TestStatus:
    """Tests for GET /api/status endpoint"""

    def test_status_success(self, client, mock_esp32_bridge):
        """Test successful status retrieval"""
        status_data = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
            "CP": 0,
            "CPV": 3931,
            "PP": 0,
            "PPV": 2457,
            "RL": 0,
            "LOCK": 0,
            "MOTOR": 0,
            "PWM": 255,
            "MAX": 32,
            "CABLE": 0,
            "AUTH": 0,
            "PB": 0,
            "STOP": 0,
            "timestamp": datetime.now().isoformat(),
        }
        mock_esp32_bridge.get_status.return_value = status_data

        response = client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["STATE"] == ESP32State.IDLE.value
        assert data["data"]["STATE_NAME"] == "IDLE"

    def test_status_esp32_disconnected(self, client, mock_esp32_bridge):
        """Test status fails when ESP32 is disconnected"""
        mock_esp32_bridge.is_connected = False

        response = client.get("/api/status")

        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "bağlantı" in data["detail"].lower()

    def test_status_stale_data(self, client, mock_esp32_bridge):
        """Test status with stale data (older than 10 seconds)"""
        # Stale data (older than 10 seconds)
        stale_timestamp = (datetime.now() - timedelta(seconds=15)).isoformat()
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
            "timestamp": stale_timestamp,
        }

        # get_status_sync should be called for fresh data
        fresh_data = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
            "CP": 0,
            "CPV": 3931,
            "PP": 0,
            "PPV": 2457,
            "RL": 0,
            "LOCK": 0,
            "MOTOR": 0,
            "PWM": 255,
            "MAX": 32,
            "CABLE": 0,
            "AUTH": 0,
            "PB": 0,
            "STOP": 0,
            "timestamp": datetime.now().isoformat(),
        }
        mock_esp32_bridge.get_status_sync.return_value = fresh_data

        response = client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_status_timeout(self, client, mock_esp32_bridge):
        """Test status when ESP32 times out"""
        mock_esp32_bridge.get_status.return_value = None
        mock_esp32_bridge.get_status_sync.return_value = None

        response = client.get("/api/status")

        assert response.status_code == 504
        data = response.json()
        assert "detail" in data
        assert "timeout" in data["detail"].lower() or "alınamadı" in data["detail"]

    def test_status_all_states(self, client, mock_esp32_bridge):
        """Test status with all possible ESP32 states"""
        for state in ESP32State:
            status_data = {
                "STATE": state.value,
                "STATE_NAME": state.name,
                "CP": 0,
                "CPV": 0,
                "PP": 0,
                "PPV": 0,
                "RL": 0,
                "LOCK": 0,
                "MOTOR": 0,
                "PWM": 0,
                "MAX": 32,
                "CABLE": 0,
                "AUTH": 0,
                "PB": 0,
                "STOP": 0,
                "timestamp": datetime.now().isoformat(),
            }
            mock_esp32_bridge.get_status.return_value = status_data

            response = client.get("/api/status")

            assert response.status_code == 200, f"State {state.name} should return 200"
            data = response.json()
            assert data["data"]["STATE"] == state.value
            assert data["data"]["STATE_NAME"] == state.name


# ============================================================================
# POST /api/maxcurrent TESTS
# ============================================================================


class TestMaxCurrent:
    """Tests for POST /api/maxcurrent endpoint"""

    def test_set_current_success_idle(self, client, mock_esp32_bridge, test_headers):
        """Test successful current set when ESP32 is in IDLE state"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
            "MAX": 16,
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20},
            headers=test_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_esp32_bridge.send_current_set.assert_called_once_with(20)

    def test_set_current_success_ev_connected(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test successful current set when ESP32 is in EV_CONNECTED state"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "STATE_NAME": "EV_CONNECTED",
            "MAX": 16,
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 25},
            headers=test_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_current_invalid_state_charging(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test current set fails when ESP32 is charging"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CHARGING.value,
            "STATE_NAME": "CHARGING",
            "MAX": 16,
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20},
            headers=test_headers,
        )

        assert response.status_code in [400, 503]
        data = response.json()
        assert "detail" in data
        assert "CHARGING" in data["detail"] or "akım değiştirilemez" in data["detail"]

    def test_set_current_invalid_state_paused(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test current set fails when ESP32 is paused"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.PAUSED.value,
            "STATE_NAME": "PAUSED",
            "MAX": 16,
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20},
            headers=test_headers,
        )

        assert response.status_code in [400, 503]
        data = response.json()
        assert "detail" in data

    def test_set_current_minimum_value(self, client, mock_esp32_bridge, test_headers):
        """Test current set with minimum valid value (6A)"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
            "MAX": 16,
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 6},
            headers=test_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_current_maximum_value(self, client, mock_esp32_bridge, test_headers):
        """Test current set with maximum valid value (32A)"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
            "MAX": 16,
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 32},
            headers=test_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_current_below_minimum(self, client, mock_esp32_bridge, test_headers):
        """Test current set with value below minimum (5A)"""
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 5},
            headers=test_headers,
        )

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_set_current_above_maximum(self, client, mock_esp32_bridge, test_headers):
        """Test current set with value above maximum (33A)"""
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 33},
            headers=test_headers,
        )

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_set_current_non_integer(self, client, mock_esp32_bridge, test_headers):
        """Test current set with non-integer value"""
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20.5},
            headers=test_headers,
        )

        assert response.status_code == 422  # Validation error

    def test_set_current_missing_field(self, client, mock_esp32_bridge, test_headers):
        """Test current set without amperage field"""
        response = client.post("/api/maxcurrent", json={}, headers=test_headers)

        assert response.status_code == 422  # Validation error

    def test_set_current_esp32_disconnected(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test current set fails when ESP32 is disconnected"""
        mock_esp32_bridge.is_connected = False

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20},
            headers=test_headers,
        )

        assert response.status_code == 503
        data = response.json()
        assert "detail" in data

    def test_set_current_all_valid_states(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test current set with all valid states"""
        valid_states = [ESP32State.IDLE, ESP32State.EV_CONNECTED, ESP32State.READY]

        for state in valid_states:
            mock_esp32_bridge.get_status.return_value = {
                "STATE": state.value,
                "STATE_NAME": state.name,
                "MAX": 16,
                "timestamp": datetime.now().isoformat(),
            }

            response = client.post(
                "/api/maxcurrent",
                json={"amperage": 20},
                headers=test_headers,
            )

            assert (
                response.status_code == 200
            ), f"State {state.name} should allow current change"

    def test_set_current_all_invalid_states(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Test current set with all invalid states"""
        invalid_states = [ESP32State.CHARGING, ESP32State.PAUSED, ESP32State.STOPPED]

        for state in invalid_states:
            mock_esp32_bridge.get_status.return_value = {
                "STATE": state.value,
                "STATE_NAME": state.name,
                "MAX": 16,
                "timestamp": datetime.now().isoformat(),
            }

            response = client.post(
                "/api/maxcurrent",
                json={"amperage": 20},
                headers=test_headers,
            )

            assert response.status_code in [
                400,
                503,
            ], f"State {state.name} should reject current change"


# ============================================================================
# EDGE CASES AND INTEGRATION TESTS
# ============================================================================


class TestEdgeCases:
    """Edge case tests for all endpoints"""

    def test_concurrent_charge_start(self, client, mock_esp32_bridge, test_headers):
        """Test concurrent charge start requests"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "STATE_NAME": "EV_CONNECTED",
            "CP": 2,
            "CPV": 1847,
            "PP": 1,
            "PPV": 1566,
            "RL": 1,
            "LOCK": 1,
            "MOTOR": 0,
            "PWM": 0,
            "MAX": 16,
            "CABLE": 20,
            "AUTH": 0,
            "PB": 0,
            "STOP": 0,
            "timestamp": datetime.now().isoformat(),
        }

        # First request should succeed
        response1 = client.post(
            "/api/charge/start",
            json={"user_id": "user-1"},
            headers=test_headers,
        )

        # Second request might fail due to state change or rate limiting
        response2 = client.post(
            "/api/charge/start",
            json={"user_id": "user-2"},
            headers=test_headers,
        )

        assert response1.status_code == 200
        # Second request might succeed or fail depending on implementation
        assert response2.status_code in [200, 400, 503, 429]

    def test_status_caching(self, client, mock_esp32_bridge):
        """Test status endpoint caching"""
        status_data = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
            "CP": 0,
            "CPV": 3931,
            "PP": 0,
            "PPV": 2457,
            "RL": 0,
            "LOCK": 0,
            "MOTOR": 0,
            "PWM": 255,
            "MAX": 32,
            "CABLE": 0,
            "AUTH": 0,
            "PB": 0,
            "STOP": 0,
            "timestamp": datetime.now().isoformat(),
        }
        mock_esp32_bridge.get_status.return_value = status_data

        # First request
        response1 = client.get("/api/status")
        assert response1.status_code == 200

        # Second request (should use cache)
        response2 = client.get("/api/status")
        assert response2.status_code == 200

        # Both should return same data (cached)
        assert response1.json() == response2.json()

    def test_current_set_boundary_values(self, client, mock_esp32_bridge, test_headers):
        """Test current set with boundary values"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
            "MAX": 16,
            "timestamp": datetime.now().isoformat(),
        }

        # Test boundary values
        boundary_tests = [
            (6, 200),  # Minimum valid
            (32, 200),  # Maximum valid
            (5, 422),  # Below minimum
            (33, 422),  # Above maximum
        ]

        for amperage, expected_status in boundary_tests:
            response = client.post(
                "/api/maxcurrent",
                json={"amperage": amperage},
                headers=test_headers,
            )
            assert (
                response.status_code == expected_status
            ), f"Amperage {amperage} should return {expected_status}"
