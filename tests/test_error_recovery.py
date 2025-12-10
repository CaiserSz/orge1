"""
Error Recovery Testleri
Created: 2025-12-10 13:25:00
Last Modified: 2025-12-10 13:25:00
Version: 1.0.0
Description: Error recovery testleri - ESP32 bağlantı kopması → Yeniden bağlanma
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import ESP32State

# conftest.py'deki standart fixture'ları kullan
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


class TestErrorRecovery:
    """Error recovery testleri"""

    def test_esp32_disconnection_recovery(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        ESP32 bağlantı kopması → Yeniden bağlanma senaryosu

        Senaryo:
        1. ESP32 bağlantısı kopmuş
        2. API endpoint'ine istek gönder (503 hatası döndürmeli)
        3. ESP32 bağlantısı yeniden kuruldu
        4. API endpoint'ine tekrar istek gönder (başarılı olmalı)
        """
        # 1. ESP32 bağlantısı kopmuş
        mock_esp32_bridge.is_connected = False
        # get_status_sync de None döndürmeli
        mock_esp32_bridge.get_status_sync.return_value = None

        # 2. Status endpoint'ine istek gönder
        response = client.get("/api/status")
        # is_connected False olduğu için 503 hatası döndürmeli
        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

        # 3. Charge start endpoint'ine istek gönder
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 503
        assert "ESP32 bağlantısı yok" in response.json()["detail"]

        # 4. ESP32 bağlantısı yeniden kuruldu
        mock_esp32_bridge.is_connected = True

        # Status için get_status ve get_status_sync mock'la
        status_data = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }
        mock_esp32_bridge.get_status.return_value = status_data
        mock_esp32_bridge.get_status_sync.return_value = status_data

        # 5. Status endpoint'ine tekrar istek gönder
        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 6. Charge start için EV_CONNECTED state'e geç
        charge_start_data = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        # Charge start içinde 2 kez get_status çağrılıyor
        mock_esp32_bridge.get_status.side_effect = [
            charge_start_data,  # İlk kontrol
            charge_start_data,  # Final kontrol
        ]

        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_esp32_status_timeout_recovery(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        ESP32 status timeout → Recovery senaryosu

        Senaryo:
        1. ESP32'den status alınamıyor (timeout)
        2. API endpoint'ine istek gönder (504 hatası döndürmeli)
        3. ESP32'den status alınabiliyor
        4. API endpoint'ine tekrar istek gönder (başarılı olmalı)
        """
        # 1. ESP32'den status alınamıyor (None döndürüyor)
        mock_esp32_bridge.get_status.return_value = None
        mock_esp32_bridge.get_status_sync.return_value = None

        # 2. Status endpoint'ine istek gönder
        response = client.get("/api/status")
        assert response.status_code == 504
        assert "ESP32'den durum bilgisi alınamadı" in response.json()["detail"]

        # 3. ESP32'den status alınabiliyor
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }
        mock_esp32_bridge.get_status_sync.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }

        # 4. Status endpoint'ine tekrar istek gönder
        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_esp32_state_none_recovery(self, client, mock_esp32_bridge, test_headers):
        """
        ESP32 STATE None → Recovery senaryosu

        Senaryo:
        1. ESP32'den STATE None geliyor
        2. Charge start endpoint'ine istek gönder (503 hatası döndürmeli)
        3. ESP32'den STATE değeri geliyor
        4. Charge start endpoint'ine tekrar istek gönder (başarılı olmalı)
        """
        # 1. ESP32'den STATE None geliyor (STATE key'i yok)
        # get_status None döndürmeli veya STATE key'i olmayan dict döndürmeli
        mock_esp32_bridge.get_status.return_value = {
            "AUTH": 0,
            "CABLE": 0,
            # STATE eksik - None olacak
        }

        # 2. Charge start endpoint'ine istek gönder
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        # STATE None olduğu için 503 hatası döndürmeli
        assert response.status_code == 503
        assert "STATE değeri alınamadı" in response.json()["detail"]

        # 3. ESP32'den STATE değeri geliyor
        charge_start_data = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        # Charge start içinde 2 kez get_status çağrılıyor
        mock_esp32_bridge.get_status.side_effect = [
            charge_start_data,  # İlk kontrol
            charge_start_data,  # Final kontrol
        ]

        # 4. Charge start endpoint'ine tekrar istek gönder
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_esp32_invalid_state_recovery(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        ESP32 invalid state → Recovery senaryosu

        Senaryo:
        1. ESP32'den geçersiz STATE değeri geliyor
        2. Charge start endpoint'ine istek gönder (503 hatası döndürmeli)
        3. ESP32'den geçerli STATE değeri geliyor
        4. Charge start endpoint'ine tekrar istek gönder (başarılı olmalı)
        """
        # 1. ESP32'den geçersiz STATE değeri geliyor (99 gibi)
        # get_status 2 kez çağrılıyor (ilk kontrol + final kontrol)
        mock_esp32_bridge.get_status.side_effect = [
            {
                "STATE": 99,  # Geçersiz state
                "AUTH": 0,
                "CABLE": 0,
            },
            {
                "STATE": 99,  # Geçersiz state (final kontrol)
                "AUTH": 0,
                "CABLE": 0,
            },
        ]

        # 2. Charge start endpoint'ine istek gönder
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 503
        assert "Geçersiz STATE değeri" in response.json()["detail"]

        # 3. ESP32'den geçerli STATE değeri geliyor
        charge_start_data = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        # Charge start içinde 2 kez get_status çağrılıyor
        mock_esp32_bridge.get_status.side_effect = [
            charge_start_data,  # İlk kontrol
            charge_start_data,  # Final kontrol
        ]

        # 4. Charge start endpoint'ine tekrar istek gönder
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_esp32_command_failure_recovery(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        ESP32 komut gönderme hatası → Recovery senaryosu

        Senaryo:
        1. ESP32'ye komut gönderilemiyor
        2. Charge start endpoint'ine istek gönder (500 hatası döndürmeli)
        3. ESP32'ye komut gönderilebiliyor
        4. Charge start endpoint'ine tekrar istek gönder (başarılı olmalı)
        """
        # 1. ESP32'ye komut gönderilemiyor
        # get_status 2 kez çağrılıyor (ilk kontrol + final kontrol)
        charge_start_data = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        mock_esp32_bridge.get_status.side_effect = [
            charge_start_data,  # İlk kontrol
            charge_start_data,  # Final kontrol
        ]
        mock_esp32_bridge.send_authorization.return_value = False

        # 2. Charge start endpoint'ine istek gönder
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 500
        assert "komutu gönderilemedi" in response.json()["detail"]

        # 3. ESP32'ye komut gönderilebiliyor
        mock_esp32_bridge.send_authorization.return_value = True

        # Charge start için get_status mock'la (2 çağrı)
        charge_start_data = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        mock_esp32_bridge.get_status.side_effect = [
            charge_start_data,  # İlk kontrol
            charge_start_data,  # Final kontrol
        ]

        # 4. Charge start endpoint'ine tekrar istek gönder
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
