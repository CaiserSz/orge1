"""
API Integration Test Scenarios
Created: 2025-12-10 10:55:00
Last Modified: 2025-12-10 10:55:00
Version: 1.0.0
Description: API endpoint'leri için integration test senaryoları
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.event_detector import ESP32State
from api.main import app

# conftest.py'den fixture'ları kullan
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


class TestChargeFlowIntegration:
    """Şarj akışı integration testleri"""

    def test_full_charge_flow(self, client, mock_esp32_bridge, test_headers):
        """
        Tam şarj akışı testi:
        1. IDLE -> CABLE_DETECT
        2. CABLE_DETECT -> EV_CONNECTED
        3. EV_CONNECTED -> READY (authorization)
        4. READY -> CHARGING
        5. CHARGING -> STOPPED
        """
        # 1. IDLE durumu
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "AUTH": 0,
            "CABLE": 0,
            "MAX": 16,
        }

        # 2. CABLE_DETECT durumu
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CABLE_DETECT.value,
            "PP": 1,
            "CABLE": 32,
        }

        # 3. EV_CONNECTED durumu - şarj başlatılabilir
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "CP": 1,
            "AUTH": 0,
        }

        # Şarj başlat
        response = client.post(
            "/api/charge/start", json={}, headers=test_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 4. READY durumu (authorization verildi)
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.READY.value,
            "AUTH": 1,
        }

        # 5. CHARGING durumu
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CHARGING.value,
            "AUTH": 1,
            "CABLE": 16,
            "MAX": 16,
        }

        # Şarj durdur
        response = client.post(
            "/api/charge/stop", json={}, headers=test_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_current_set_before_charge(self, client, mock_esp32_bridge, test_headers):
        """
        Şarj öncesi akım ayarlama testi
        """
        # IDLE durumunda akım ayarlanabilir
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }

        # Akım ayarla
        response = client.post(
            "/api/maxcurrent", json={"amperage": 20}, headers=test_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_current_set_during_charge_fails(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        Şarj esnasında akım değiştirme denemesi reddedilmeli
        """
        # CHARGING durumu
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CHARGING.value,
            "AUTH": 1,
            "CABLE": 16,
            "MAX": 16,
        }

        # Akım değiştirme denemesi
        response = client.post(
            "/api/maxcurrent", json={"amperage": 20}, headers=test_headers
        )
        assert response.status_code == 400
        assert "akım değiştirilemez" in response.json()["detail"].lower()


class TestErrorRecoveryScenarios:
    """Hata kurtarma senaryoları"""

    def test_bridge_disconnected_recovery(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        Bridge bağlantısı kesildiğinde hata döndürülmeli
        """
        mock_esp32_bridge.is_connected = False

        # Health check
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["data"]["esp32_connected"] is False

        # Status check
        response = client.get("/api/status")
        assert response.status_code == 503

    def test_invalid_state_transition(self, client, mock_esp32_bridge, test_headers):
        """
        Geçersiz state geçişi reddedilmeli
        """
        # IDLE durumunda şarj başlatılamaz
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
        }

        response = client.post(
            "/api/charge/start", json={}, headers=test_headers
        )
        assert response.status_code == 400
        assert "başlatılamaz" in response.json()["detail"].lower()


class TestEndpointCombinations:
    """Endpoint kombinasyon testleri"""

    def test_multiple_current_changes(self, client, mock_esp32_bridge, test_headers):
        """
        Birden fazla akım değişikliği
        """
        # IDLE durumunda
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }

        # İlk akım ayarı
        response = client.post(
            "/api/maxcurrent", json={"amperage": 10}, headers=test_headers
        )
        assert response.status_code == 200

        # İkinci akım ayarı
        response = client.post(
            "/api/maxcurrent", json={"amperage": 20}, headers=test_headers
        )
        assert response.status_code == 200

        # Üçüncü akım ayarı
        response = client.post(
            "/api/maxcurrent", json={"amperage": 32}, headers=test_headers
        )
        assert response.status_code == 200

    def test_charge_start_stop_cycle(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        Şarj başlat-durdur döngüsü
        """
        # EV_CONNECTED durumu
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
        }

        # Şarj başlat
        response = client.post(
            "/api/charge/start", json={}, headers=test_headers
        )
        assert response.status_code == 200

        # Şarj durdur
        response = client.post(
            "/api/charge/stop", json={}, headers=test_headers
        )
        assert response.status_code == 200

        # Tekrar şarj başlat
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
        }
        response = client.post(
            "/api/charge/start", json={}, headers=test_headers
        )
        assert response.status_code == 200

