"""
API Edge Cases and Error Handling Tests
Created: 2025-12-09 23:10:00
Last Modified: 2025-12-09 23:10:00
Version: 1.0.0
Description: API endpoint'leri için edge case ve error handling testleri
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import HTTPException, status

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from esp32.bridge import ESP32Bridge


class TestAPIEdgeCases:
    """API endpoint'leri için edge case testleri"""

    def setup_method(self):
        """Her test öncesi test client oluştur"""
        self.client = TestClient(app)
        self.mock_bridge = Mock(spec=ESP32Bridge)
        self.mock_bridge.is_connected = True
        self.mock_bridge.get_status = Mock(return_value={"STATE": 1})
        self.mock_bridge.get_status_sync = Mock(return_value={"STATE": 1})
        self.mock_bridge.send_authorization = Mock(return_value=True)
        self.mock_bridge.send_charge_stop = Mock(return_value=True)
        self.mock_bridge.send_current_set = Mock(return_value=True)

    @patch('api.main.get_esp32_bridge')
    def test_health_check_bridge_none(self, mock_get_bridge):
        """Health check - bridge None durumu"""
        mock_get_bridge.return_value = None

        response = self.client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["esp32_connected"] is False

    @patch('api.main.get_esp32_bridge')
    def test_health_check_bridge_not_connected(self, mock_get_bridge):
        """Health check - bridge bağlı değil"""
        self.mock_bridge.is_connected = False
        mock_get_bridge.return_value = self.mock_bridge

        response = self.client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["esp32_connected"] is False

    @patch('api.main.get_esp32_bridge')
    def test_status_bridge_none(self, mock_get_bridge):
        """Status endpoint - bridge None durumu"""
        mock_get_bridge.return_value = None

        response = self.client.get("/api/status")

        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    def test_status_bridge_not_connected(self, mock_get_bridge):
        """Status endpoint - bridge bağlı değil"""
        self.mock_bridge.is_connected = False
        mock_get_bridge.return_value = self.mock_bridge

        response = self.client.get("/api/status")

        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    def test_status_no_status_data(self, mock_get_bridge):
        """Status endpoint - status data yok"""
        self.mock_bridge.get_status.return_value = None
        self.mock_bridge.get_status_sync.return_value = None
        mock_get_bridge.return_value = self.mock_bridge

        response = self.client.get("/api/status")

        assert response.status_code == 504
        assert "durum bilgisi alınamadı" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_start_charge_bridge_none(self, mock_get_bridge):
        """Start charge - bridge None durumu"""
        mock_get_bridge.return_value = None

        response = self.client.post(
            "/api/charge/start",
            json={},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_start_charge_state_5_charging(self, mock_get_bridge):
        """Start charge - STATE=5 (CHARGING) durumu"""
        self.mock_bridge.get_status.return_value = {"STATE": 5}
        mock_get_bridge.return_value = self.mock_bridge

        response = self.client.post(
            "/api/charge/start",
            json={},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 400
        assert "Şarj başlatılamaz" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_start_charge_state_8_fault(self, mock_get_bridge):
        """Start charge - STATE=8 (FAULT_HARD) durumu"""
        self.mock_bridge.get_status.return_value = {"STATE": 8}
        mock_get_bridge.return_value = self.mock_bridge

        response = self.client.post(
            "/api/charge/start",
            json={},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 400
        assert "Şarj başlatılamaz" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_start_charge_authorization_failure(self, mock_get_bridge):
        """Start charge - authorization komutu başarısız"""
        self.mock_bridge.get_status.return_value = {"STATE": 1}
        self.mock_bridge.send_authorization.return_value = False
        mock_get_bridge.return_value = self.mock_bridge

        response = self.client.post(
            "/api/charge/start",
            json={},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 500
        assert "komutu gönderilemedi" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_stop_charge_bridge_none(self, mock_get_bridge):
        """Stop charge - bridge None durumu"""
        mock_get_bridge.return_value = None

        response = self.client.post(
            "/api/charge/stop",
            json={},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_stop_charge_command_failure(self, mock_get_bridge):
        """Stop charge - komut başarısız"""
        self.mock_bridge.send_charge_stop.return_value = False
        mock_get_bridge.return_value = self.mock_bridge

        response = self.client.post(
            "/api/charge/stop",
            json={},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 500
        assert "komutu gönderilemedi" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_set_current_bridge_none(self, mock_get_bridge):
        """Set current - bridge None durumu"""
        mock_get_bridge.return_value = None

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_set_current_state_5_charging(self, mock_get_bridge):
        """Set current - STATE=5 (CHARGING) durumu"""
        self.mock_bridge.get_status.return_value = {"STATE": 5}
        mock_get_bridge.return_value = self.mock_bridge

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 400
        assert "akım değiştirilemez" in response.json()["detail"].lower()

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_set_current_command_failure(self, mock_get_bridge):
        """Set current - komut başarısız"""
        self.mock_bridge.get_status.return_value = {"STATE": 1}
        self.mock_bridge.send_current_set.return_value = False
        mock_get_bridge.return_value = self.mock_bridge

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 500
        assert "komutu gönderilemedi" in response.json()["detail"]

    @patch('api.main.get_esp32_bridge')
    def test_get_available_currents(self, mock_get_bridge):
        """Get available currents - her zaman başarılı"""
        response = self.client.get("/api/current/available")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "range" in data["data"]
        assert data["data"]["min"] == 6
        assert data["data"]["max"] == 32


class TestAPIInputValidation:
    """API input validation testleri"""

    def setup_method(self):
        """Her test öncesi test client oluştur"""
        self.client = TestClient(app)

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_set_current_boundary_min(self, mock_get_bridge):
        """Set current - minimum değer (6A)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": 1}
        mock_bridge.send_current_set.return_value = True
        mock_get_bridge.return_value = mock_bridge

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 6},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 200
        mock_bridge.send_current_set.assert_called_once_with(6)

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_set_current_boundary_max(self, mock_get_bridge):
        """Set current - maksimum değer (32A)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": 1}
        mock_bridge.send_current_set.return_value = True
        mock_get_bridge.return_value = mock_bridge

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 32},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 200
        mock_bridge.send_current_set.assert_called_once_with(32)

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_set_current_invalid_below_min(self, mock_get_bridge):
        """Set current - minimum altı (5A)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": 1}
        mock_get_bridge.return_value = mock_bridge

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 5},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 422  # Validation error

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_set_current_invalid_above_max(self, mock_get_bridge):
        """Set current - maksimum üstü (33A)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": 1}
        mock_get_bridge.return_value = mock_bridge

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": 33},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 422  # Validation error

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_set_current_missing_field(self, mock_get_bridge):
        """Set current - eksik field"""
        response = self.client.post(
            "/api/maxcurrent",
            json={},
            headers={"X-API-Key": "test-key-123"}
        )

        assert response.status_code == 422  # Validation error

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_set_current_invalid_type(self, mock_get_bridge):
        """Set current - geçersiz tip (string)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": 1}
        mock_get_bridge.return_value = mock_bridge

        response = self.client.post(
            "/api/maxcurrent",
            json={"amperage": "16"},
            headers={"X-API-Key": "test-key-123"}
        )

        # Pydantic string'i integer'a çevirebilir, bu yüzden 200 veya 422 olabilir
        assert response.status_code in [200, 422]


class TestAPIErrorHandling:
    """API error handling testleri"""

    def setup_method(self):
        """Her test öncesi test client oluştur"""
        self.client = TestClient(app)

    def test_global_exception_handler(self):
        """Global exception handler testi"""
        # Exception'ı endpoint içinde oluştur
        with patch('api.main.get_bridge', side_effect=Exception("Test exception")):
            response = self.client.get("/api/status")

            # Exception handler çalışmalı - 500 veya başka bir hata kodu
            assert response.status_code >= 500

    def test_invalid_endpoint(self):
        """Geçersiz endpoint"""
        response = self.client.get("/api/invalid")

        assert response.status_code == 404

    def test_invalid_method(self):
        """Geçersiz HTTP method"""
        response = self.client.delete("/api/status")

        assert response.status_code == 405  # Method not allowed


class TestAPIStateEdgeCases:
    """API state edge case testleri"""

    def setup_method(self):
        """Her test öncesi test client oluştur"""
        self.client = TestClient(app)

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_start_charge_all_valid_states(self, mock_get_bridge):
        """Start charge - tüm geçerli state'ler (1-4)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.send_authorization.return_value = True
        mock_get_bridge.return_value = mock_bridge

        valid_states = [1, 2, 3, 4]
        for state in valid_states:
            mock_bridge.get_status.return_value = {"STATE": state}

            response = self.client.post(
                "/api/charge/start",
                json={},
                headers={"X-API-Key": "test-key-123"}
            )

            assert response.status_code == 200, f"State {state} için başarısız"

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_set_current_all_valid_states(self, mock_get_bridge):
        """Set current - tüm geçerli state'ler (1-4)"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.send_current_set.return_value = True
        mock_get_bridge.return_value = mock_bridge

        valid_states = [1, 2, 3, 4]
        for state in valid_states:
            mock_bridge.get_status.return_value = {"STATE": state}

            response = self.client.post(
                "/api/maxcurrent",
                json={"amperage": 16},
                headers={"X-API-Key": "test-key-123"}
            )

            assert response.status_code == 200, f"State {state} için başarısız"

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
    def test_start_charge_state_none(self, mock_get_bridge):
        """Start charge - STATE None durumu"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = None
        mock_bridge.send_authorization.return_value = True
        mock_get_bridge.return_value = mock_bridge

        response = self.client.post(
            "/api/charge/start",
            json={},
            headers={"X-API-Key": "test-key-123"}
        )

        # STATE None ise şarj başlatılabilir (default davranış)
        assert response.status_code == 200

    @patch('api.main.get_esp32_bridge')
    @patch.dict('os.environ', {'SECRET_API_KEY': 'test-key-123'})
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
            headers={"X-API-Key": "test-key-123"}
        )

        # STATE None ise akım ayarlanabilir (default davranış)
        assert response.status_code == 200

