"""
API Endpoints Unit Tests
Created: 2025-12-09 02:00:00
Last Modified: 2025-12-09 02:00:00
Version: 1.0.0
Description: API endpoint'leri için unit testler - Mock ESP32 bridge ile
"""

import sys
from pathlib import Path

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import ESP32State

# conftest.py'den fixture'ları import et
# pytest otomatik olarak conftest.py'deki fixture'ları bulur
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


class TestAPIEndpoints:
    """API endpoint testleri"""

    def test_health_check(self, client):
        """Health check endpoint çalışıyor mu?"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["api"] == "healthy"
        assert data["data"]["esp32_connected"] is True

    def test_status_endpoint(self, client, mock_esp32_bridge):
        """Status endpoint çalışıyor mu?"""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "STATE" in data["data"]
        # RL/LOCK gibi firmware/hardware'a bağlı telemetri alanları için açıklama bloğu
        assert "telemetry" in data["data"]
        mock_esp32_bridge.get_status.assert_called()

    def test_start_charge_endpoint(self, client, mock_esp32_bridge, test_headers):
        """Start charge endpoint çalışıyor mu?"""
        # Mock bridge'i EV_CONNECTED state'e ayarla
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
            "MAX": 16,
        }
        response = client.post("/api/charge/start", json={}, headers=test_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Şarj başlatma komutu gönderildi"
        mock_esp32_bridge.send_authorization.assert_called_once()

    def test_stop_charge_endpoint(self, client, mock_esp32_bridge, test_headers):
        """Stop charge endpoint çalışıyor mu?"""
        response = client.post("/api/charge/stop", json={}, headers=test_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Şarj durdurma komutu gönderildi"
        mock_esp32_bridge.send_charge_stop.assert_called_once()

    def test_set_current_8A(self, client, mock_esp32_bridge, test_headers):
        """Set current 8A endpoint çalışıyor mu?"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": 8}, headers=test_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "8A" in data["message"]
        mock_esp32_bridge.send_current_set.assert_called_once_with(8)

    def test_set_current_16A(self, client, mock_esp32_bridge, test_headers):
        """Set current 16A endpoint çalışıyor mu?"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": 16}, headers=test_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "16A" in data["message"]
        mock_esp32_bridge.send_current_set.assert_called_once_with(16)

    def test_set_current_24A(self, client, mock_esp32_bridge, test_headers):
        """Set current 24A endpoint çalışıyor mu?"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": 24}, headers=test_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "24A" in data["message"]
        mock_esp32_bridge.send_current_set.assert_called_once_with(24)

    def test_set_current_32A(self, client, mock_esp32_bridge, test_headers):
        """Set current 32A endpoint çalışıyor mu?"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": 32}, headers=test_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "32A" in data["message"]
        mock_esp32_bridge.send_current_set.assert_called_once_with(32)

    def test_set_current_invalid_low(self, client):
        """Geçersiz düşük akım değeri reddedilmeli"""
        response = client.post("/api/maxcurrent", json={"amperage": 5})
        assert response.status_code == 422  # Validation error

    def test_set_current_invalid_high(self, client):
        """Geçersiz yüksek akım değeri reddedilmeli"""
        response = client.post("/api/maxcurrent", json={"amperage": 33})
        assert response.status_code == 422  # Validation error

    def test_start_charge_when_already_charging(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Aktif şarj varken tekrar başlatma denemesi reddedilmeli"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CHARGING.value,  # CHARGING
            "AUTH": 1,
            "CABLE": 16,
            "MAX": 16,
        }

        response = client.post("/api/charge/start", json={}, headers=test_headers)
        assert response.status_code == 400
        assert "zaten aktif" in response.json()["detail"].lower()

    def test_set_current_when_charging(self, client, mock_esp32_bridge, test_headers):
        """Şarj aktifken akım değiştirme denemesi reddedilmeli"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CHARGING.value,  # CHARGING
            "AUTH": 1,
            "CABLE": 16,
            "MAX": 16,
        }

        response = client.post(
            "/api/maxcurrent", json={"amperage": 24}, headers=test_headers
        )
        assert response.status_code == 400
        assert "aktifken" in response.json()["detail"].lower()
