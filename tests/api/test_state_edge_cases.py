"""
API State Edge Cases Tests
Created: 2025-12-09 23:10:00
Last Modified: 2025-12-10 09:00:00
Version: 1.0.0
Description: API state edge case testleri
"""

import sys
from unittest.mock import Mock, patch
from pathlib import Path
from fastapi.testclient import TestClient

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.main import app
from api.event_detector import ESP32State
from esp32.bridge import ESP32Bridge


class TestAPIStateEdgeCases:
    """API state edge case testleri"""

    def setup_method(self):
        """Her test öncesi test client oluştur"""
        self.client = TestClient(app)

    @patch("api.main.get_esp32_bridge")
    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_start_charge_all_valid_states(self, mock_get_bridge):
        """Start charge - tüm geçerli state'ler"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.send_authorization.return_value = True
        mock_get_bridge.return_value = mock_bridge

        valid_states = [
            ESP32State.IDLE.value,
            ESP32State.CABLE_DETECT.value,
            ESP32State.EV_CONNECTED.value,
            ESP32State.READY.value,
        ]
        for state in valid_states:
            mock_bridge.get_status.return_value = {"STATE": state}

            response = self.client.post(
                "/api/charge/start", json={}, headers={"X-API-Key": "test-key-123"}
            )

            assert response.status_code == 200, f"State {state} için başarısız"

    @patch("api.main.get_esp32_bridge")
    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_all_valid_states(self, mock_get_bridge):
        """Set current - tüm geçerli state'ler"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.send_current_set.return_value = True
        mock_get_bridge.return_value = mock_bridge

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

    @patch("api.main.get_esp32_bridge")
    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_start_charge_state_none(self, mock_get_bridge):
        """Start charge - STATE None durumu"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = None
        mock_bridge.send_authorization.return_value = True
        mock_get_bridge.return_value = mock_bridge

        response = self.client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-key-123"}
        )

        # STATE None ise şarj başlatılabilir (default davranış)
        assert response.status_code == 200

    @patch("api.main.get_esp32_bridge")
    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_state_none(self, mock_get_bridge):
        """Set current - STATE None durumu"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = None
        mock_bridge.send_current_set.return_value = True
        mock_get_bridge.return_value = mock_bridge

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-key-123"},
        )

        # STATE None ise akım ayarlanabilir (default davranış)
        assert response.status_code == 200
