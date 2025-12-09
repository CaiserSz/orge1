"""
API Endpoints Unit Tests
Created: 2025-12-09 02:00:00
Last Modified: 2025-12-09 02:00:00
Version: 1.0.0
Description: API endpoint'leri için unit testler - Mock ESP32 bridge ile
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
from fastapi.testclient import TestClient

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app


@pytest.fixture
def mock_esp32_bridge():
    """Mock ESP32 bridge fixture"""
    mock_bridge = Mock()
    mock_bridge.is_connected = True
    mock_bridge.get_status = Mock(return_value={
        'STATE': 1,
        'AUTH': 0,
        'CABLE': 0,
        'MAX': 16,
        'CP': 0,
        'PP': 0,
        'CPV': 3920,
        'PPV': 2455,
        'RL': 0,
        'LOCK': 0,
        'MOTOR': 0,
        'PWM': 255,
        'PB': 0,
        'STOP': 0
    })
    mock_bridge.send_authorization = Mock(return_value=True)
    mock_bridge.send_charge_stop = Mock(return_value=True)
    mock_bridge.send_current_set = Mock(return_value=True)
    return mock_bridge


@pytest.fixture
def client(mock_esp32_bridge):
    """Test client fixture"""
    import os
    # Test için API key set et
    os.environ['SECRET_API_KEY'] = 'test-api-key'

    with patch('api.routers.dependencies.get_bridge', return_value=mock_esp32_bridge):
        with patch('esp32.bridge.get_esp32_bridge', return_value=mock_esp32_bridge):
            yield TestClient(app)


class TestAPIEndpoints:
    """API endpoint testleri"""

    def test_health_check(self, client):
        """Health check endpoint çalışıyor mu?"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['api'] == 'healthy'
        assert data['data']['esp32_connected'] is True

    def test_status_endpoint(self, client, mock_esp32_bridge):
        """Status endpoint çalışıyor mu?"""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'data' in data
        assert 'STATE' in data['data']
        mock_esp32_bridge.get_status.assert_called()

    def test_start_charge_endpoint(self, client, mock_esp32_bridge):
        """Start charge endpoint çalışıyor mu?"""
        response = client.post(
            "/api/charge/start",
            json={},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "Şarj başlatma komutu gönderildi"
        mock_esp32_bridge.send_authorization.assert_called_once()

    def test_stop_charge_endpoint(self, client, mock_esp32_bridge):
        """Stop charge endpoint çalışıyor mu?"""
        response = client.post(
            "/api/charge/stop",
            json={},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "Şarj durdurma komutu gönderildi"
        mock_esp32_bridge.send_charge_stop.assert_called_once()

    def test_set_current_8A(self, client, mock_esp32_bridge):
        """Set current 8A endpoint çalışıyor mu?"""
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 8},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert "8A" in data['message']
        mock_esp32_bridge.send_current_set.assert_called_once_with(8)

    def test_set_current_16A(self, client, mock_esp32_bridge):
        """Set current 16A endpoint çalışıyor mu?"""
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert "16A" in data['message']
        mock_esp32_bridge.send_current_set.assert_called_once_with(16)

    def test_set_current_24A(self, client, mock_esp32_bridge):
        """Set current 24A endpoint çalışıyor mu?"""
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 24},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert "24A" in data['message']
        mock_esp32_bridge.send_current_set.assert_called_once_with(24)

    def test_set_current_32A(self, client, mock_esp32_bridge):
        """Set current 32A endpoint çalışıyor mu?"""
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 32},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert "32A" in data['message']
        mock_esp32_bridge.send_current_set.assert_called_once_with(32)

    def test_set_current_invalid_low(self, client):
        """Geçersiz düşük akım değeri reddedilmeli"""
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 5}
        )
        assert response.status_code == 422  # Validation error

    def test_set_current_invalid_high(self, client):
        """Geçersiz yüksek akım değeri reddedilmeli"""
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 33}
        )
        assert response.status_code == 422  # Validation error

    def test_start_charge_when_already_charging(self, client, mock_esp32_bridge):
        """Aktif şarj varken tekrar başlatma denemesi reddedilmeli"""
        mock_esp32_bridge.get_status.return_value = {
            'STATE': 5,  # SARJ_BASLADI
            'AUTH': 1,
            'CABLE': 16,
            'MAX': 16
        }

        response = client.post(
            "/api/charge/start",
            json={},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 400
        assert "zaten aktif" in response.json()['detail'].lower()

    def test_set_current_when_charging(self, client, mock_esp32_bridge):
        """Şarj aktifken akım değiştirme denemesi reddedilmeli"""
        mock_esp32_bridge.get_status.return_value = {
            'STATE': 5,  # SARJ_BASLADI
            'AUTH': 1,
            'CABLE': 16,
            'MAX': 16
        }

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 24},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 400
        assert "aktifken" in response.json()['detail'].lower()

