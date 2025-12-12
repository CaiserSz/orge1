"""
API Edge Cases Tests
Created: 2025-12-09 23:10:00
Last Modified: 2025-12-11 19:58:00
Version: 1.0.2
Description: API endpoint'leri için edge case testleri
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


class TestAPIEdgeCases:
    """API endpoint'leri için edge case testleri"""

    def setup_method(self):
        """Her test öncesi test client oluştur"""
        self.client = TestClient(app, raise_server_exceptions=False)
        self.mock_bridge = Mock(spec=ESP32Bridge)
        self.mock_bridge.is_connected = True
        self.mock_bridge.get_status = Mock(
            return_value={"STATE": ESP32State.IDLE.value}
        )
        self.mock_bridge.get_status_sync = Mock(
            return_value={"STATE": ESP32State.IDLE.value}
        )
        self.mock_bridge.send_authorization = Mock(return_value=True)
        self.mock_bridge.send_charge_stop = Mock(return_value=True)
        self.mock_bridge.send_current_set = Mock(return_value=True)
        # Varsayılan override: mock bridge
        self._set_bridge_override(self.mock_bridge)

    def teardown_method(self):
        app.dependency_overrides.pop(dependencies.get_bridge, None)

    @staticmethod
    def _set_bridge_override(bridge):
        app.dependency_overrides[dependencies.get_bridge] = lambda: bridge

    def test_health_check_bridge_none(self):
        """Health check - bridge None durumu"""
        app.dependency_overrides[dependencies.get_bridge] = lambda: None

        response = self.client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["esp32_connected"] is False

    def test_health_check_bridge_not_connected(self):
        """Health check - bridge bağlı değil"""
        self.mock_bridge.is_connected = False
        app.dependency_overrides[dependencies.get_bridge] = lambda: self.mock_bridge

        response = self.client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["esp32_connected"] is False

    def test_status_bridge_none(self):
        """Status endpoint - bridge None durumu"""
        self._set_bridge_override(None)

        response = self.client.get("/api/status")

        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

    def test_status_bridge_not_connected(self):
        """Status endpoint - bridge bağlı değil"""
        self.mock_bridge.is_connected = False

        response = self.client.get("/api/status")

        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

    def test_status_no_status_data(self):
        """Status endpoint - status data yok"""
        self.mock_bridge.get_status.return_value = None
        self.mock_bridge.get_status_sync.return_value = None

        response = self.client.get("/api/status")

        assert response.status_code == 504
        assert "durum bilgisi alınamadı" in response.json()["detail"]

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_start_charge_bridge_none(self):
        """Start charge - bridge None durumu"""
        self._set_bridge_override(None)

        response = self.client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_start_charge_state_5_charging(self):
        """Start charge - STATE=5 (CHARGING) durumu"""
        self.mock_bridge.get_status.return_value = {"STATE": ESP32State.CHARGING.value}

        response = self.client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 400
        assert "Şarj başlatılamaz" in response.json()["detail"]

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_start_charge_state_8_fault(self):
        """Start charge - STATE=8 (FAULT_HARD) durumu"""
        self.mock_bridge.get_status.return_value = {
            "STATE": ESP32State.FAULT_HARD.value
        }

        response = self.client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 400
        assert "Şarj başlatılamaz" in response.json()["detail"]

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_start_charge_authorization_failure(self):
        """Start charge - authorization komutu başarısız"""
        self.mock_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value
        }
        self.mock_bridge.send_authorization.return_value = False

        response = self.client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 500
        assert "komutu gönderilemedi" in response.json()["detail"]

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_stop_charge_bridge_none(self):
        """Stop charge - bridge None durumu"""
        self._set_bridge_override(None)

        response = self.client.post(
            "/api/charge/stop", json={}, headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_stop_charge_command_failure(self):
        """Stop charge - komut başarısız"""
        self.mock_bridge.send_charge_stop.return_value = False

        response = self.client.post(
            "/api/charge/stop", json={}, headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 500
        assert "komutu gönderilemedi" in response.json()["detail"]

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_bridge_none(self):
        """Set current - bridge None durumu"""
        self._set_bridge_override(None)

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-key-123"},
        )

        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_state_5_charging(self):
        """Set current - STATE=5 (CHARGING) durumu"""
        self.mock_bridge.get_status.return_value = {"STATE": ESP32State.CHARGING.value}

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-key-123"},
        )

        assert response.status_code == 400
        assert "akım değiştirilemez" in response.json()["detail"].lower()

    @patch.dict("os.environ", {"SECRET_API_KEY": "test-key-123"})
    def test_set_current_command_failure(self):
        """Set current - komut başarısız"""
        self.mock_bridge.get_status.return_value = {"STATE": ESP32State.IDLE.value}
        self.mock_bridge.send_current_set.return_value = False

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-key-123"},
        )

        assert response.status_code == 500
        assert "komutu gönderilemedi" in response.json()["detail"]

    def test_get_available_currents(self):
        """Get available currents - her zaman başarılı"""
        response = self.client.get("/api/current/available")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "range" in data["data"]
        assert data["data"]["min"] == 6
        assert data["data"]["max"] == 32
