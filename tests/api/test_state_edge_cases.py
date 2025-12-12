"""
API State Edge Cases Tests
Created: 2025-12-09 23:10:00
Last Modified: 2025-12-11 20:05:00
Version: 1.0.4
Description: API state edge case testleri
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api import config as config_module
from api.event_detector import ESP32State
from api.main import app
from api.routers import dependencies
from esp32.bridge import ESP32Bridge


class TestAPIStateEdgeCases:
    """API state edge case testleri"""

    def setup_method(self):
        """Her test öncesi test client oluştur"""
        self.client = TestClient(app, raise_server_exceptions=False)
        config_module.config.load()
        self._set_bridge_override(None)

    def teardown_method(self):
        app.dependency_overrides.pop(dependencies.get_bridge, None)

    @staticmethod
    def _set_bridge_override(bridge):
        app.dependency_overrides[dependencies.get_bridge] = lambda: bridge

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_start_charge_all_valid_states(self):
        """Start charge - state bazlı izinler"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.send_authorization.return_value = True
        self._set_bridge_override(mock_bridge)

        state_expectations = {
            ESP32State.IDLE.value: 400,
            ESP32State.CABLE_DETECT.value: 400,
            ESP32State.EV_CONNECTED.value: 200,
            ESP32State.READY.value: 400,
        }

        for state, expected_status in state_expectations.items():
            mock_bridge.get_status.return_value = {"STATE": state}
            response = self.client.post(
                "/api/charge/start", json={}, headers={"X-API-Key": "test-key-123"}
            )
            assert (
                response.status_code == expected_status
            ), f"State {state} için beklenen durum {expected_status}"

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_all_valid_states(self):
        """Set current - tüm geçerli state'ler"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.send_current_set.return_value = True
        self._set_bridge_override(mock_bridge)

        valid_states = [
            ESP32State.IDLE.value,
            ESP32State.CABLE_DETECT.value,
            ESP32State.EV_CONNECTED.value,
            ESP32State.READY.value,
        ]
        for state in valid_states:
            mock_bridge.get_status.return_value = {"STATE": state}
            response = self.client.post(
                "/api/maxcurrent",
                json={"amperage": 16},
                headers={"X-API-Key": "test-key-123"},
            )
            assert response.status_code == 200, f"State {state} için başarısız"

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_start_charge_state_none(self):
        """Start charge - STATE None durumu"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = None
        mock_bridge.send_authorization.return_value = True
        self._set_bridge_override(mock_bridge)

        response = self.client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 503

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_state_none(self):
        """Set current - STATE None durumu"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = None
        mock_bridge.send_current_set.return_value = True
        self._set_bridge_override(mock_bridge)

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-key-123"},
        )

        assert response.status_code == 200
