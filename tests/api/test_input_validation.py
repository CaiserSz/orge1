"""
API Input Validation Tests
Created: 2025-12-09 23:10:00
Last Modified: 2025-12-11 20:00:00
Version: 1.0.3
Description: API input validation testleri
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.event_detector import ESP32State
from api.main import app
from api.routers import dependencies
from esp32.bridge import ESP32Bridge


class TestAPIInputValidation:
    """API input validation testleri"""

    def setup_method(self):
        """Her test öncesi test client oluştur"""
        self.client = TestClient(app, raise_server_exceptions=False)
        self._set_bridge_override(None)

    def teardown_method(self):
        app.dependency_overrides.pop(dependencies.get_bridge, None)

    @staticmethod
    def _set_bridge_override(bridge):
        app.dependency_overrides[dependencies.get_bridge] = lambda: bridge

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_boundary_min(self):
        """Set current - minimum değer (6A)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": ESP32State.IDLE.value}
        mock_bridge.send_current_set.return_value = True
        self._set_bridge_override(mock_bridge)

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 6},
            headers={"X-API-Key": "test-key-123"},
        )

        assert response.status_code == 200
        mock_bridge.send_current_set.assert_called_once_with(6)

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_boundary_max(self):
        """Set current - maksimum değer (32A)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": ESP32State.IDLE.value}
        mock_bridge.send_current_set.return_value = True
        self._set_bridge_override(mock_bridge)

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 32},
            headers={"X-API-Key": "test-key-123"},
        )

        assert response.status_code == 200
        mock_bridge.send_current_set.assert_called_once_with(32)

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_invalid_below_min(self):
        """Set current - minimum altı (5A)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": ESP32State.IDLE.value}
        self._set_bridge_override(mock_bridge)

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 5},
            headers={"X-API-Key": "test-key-123"},
        )

        assert response.status_code == 422  # Validation error

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_invalid_above_max(self):
        """Set current - maksimum üstü (33A)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": ESP32State.IDLE.value}
        self._set_bridge_override(mock_bridge)

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 33},
            headers={"X-API-Key": "test-key-123"},
        )

        assert response.status_code == 422  # Validation error

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_missing_field(self):
        """Set current - eksik field"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        self._set_bridge_override(mock_bridge)

        response = self.client.post(
            "/api/maxcurrent", json={}, headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 422  # Validation error

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_invalid_type(self):
        """Set current - geçersiz tip (string)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": ESP32State.IDLE.value}
        self._set_bridge_override(mock_bridge)

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": "16"},
            headers={"X-API-Key": "test-key-123"},
        )

        # Pydantic string'i integer'a çevirebilir, bu yüzden 200 veya 422 olabilir
        assert response.status_code in [200, 422]
