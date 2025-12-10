"""
Endpoint Kombinasyon Testleri
Created: 2025-12-10 13:20:00
Last Modified: 2025-12-10 13:20:00
Version: 1.0.0
Description: Endpoint kombinasyon testleri - Charge start → Charge stop → Charge start
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import ESP32State

# conftest.py'deki standart fixture'ları kullan
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


class TestEndpointCombinations:
    """Endpoint kombinasyon testleri"""

    def test_charge_start_stop_start_combination(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        Endpoint kombinasyon testi: Charge start → Charge stop → Charge start

        Senaryo:
        1. EV_CONNECTED state'inde şarj başlat
        2. Şarjı durdur
        3. Tekrar EV_CONNECTED state'ine geç ve şarj başlat
        """
        # charge.py'de get_status() iki kez çağrılıyor (ilk kontrol + final kontrol)
        # return_value kullanarak her çağrıda aynı değeri döndür

        # İlk charge start için EV_CONNECTED state
        ev_connected_data = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        mock_esp32_bridge.get_status.return_value = ev_connected_data

        # 1. İlk şarj başlatma
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 2. Şarj durdurma (CHARGING state'inde)
        charging_data = {
            "STATE": ESP32State.CHARGING.value,
            "AUTH": 1,
            "CABLE": 16,
        }
        mock_esp32_bridge.get_status.return_value = charging_data

        response = client.post(
            "/api/charge/stop",
            json={},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 3. İkinci şarj başlatma için tekrar EV_CONNECTED state'e geç
        mock_esp32_bridge.get_status.return_value = ev_connected_data

        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_current_set_charge_start_combination(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        Endpoint kombinasyon testi: Current set → Charge start

        Senaryo:
        1. Akım ayarla
        2. Şarj başlat
        """
        # Current set için IDLE state
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }

        # 1. Akım ayarlama
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 2. Charge start için EV_CONNECTED state'e geç
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "MAX": 20,
            "AUTH": 0,
            "CABLE": 0,
        }

        # 3. Şarj başlatma
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_status_charge_start_stop_combination(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        Endpoint kombinasyon testi: Status → Charge start → Charge stop

        Senaryo:
        1. Status kontrolü
        2. Şarj başlat
        3. Status kontrolü
        4. Şarj durdur
        5. Status kontrolü
        """
        # Status endpoint'i için get_status_sync de mock'lanmalı
        ev_connected_data = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        mock_esp32_bridge.get_status.return_value = ev_connected_data
        mock_esp32_bridge.get_status_sync.return_value = ev_connected_data

        # 1. İlk status kontrolü
        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["data"]["STATE"] == ESP32State.EV_CONNECTED.value

        # 2. Şarj başlatma (EV_CONNECTED state'inde)
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 200

        # 3. İkinci status kontrolü - CHARGING
        charging_data = {
            "STATE": ESP32State.CHARGING.value,
            "AUTH": 1,
            "CABLE": 16,
        }
        mock_esp32_bridge.get_status.return_value = charging_data
        mock_esp32_bridge.get_status_sync.return_value = charging_data

        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["data"]["STATE"] == ESP32State.CHARGING.value

        # 4. Şarj durdurma
        response = client.post(
            "/api/charge/stop",
            json={},
            headers=test_headers,
        )
        assert response.status_code == 200

        # 5. Son status kontrolü - STOPPED
        stopped_data = {
            "STATE": ESP32State.STOPPED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        mock_esp32_bridge.get_status.return_value = stopped_data
        mock_esp32_bridge.get_status_sync.return_value = stopped_data

        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["data"]["STATE"] == ESP32State.STOPPED.value

    def test_multiple_charge_start_stop_cycles(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        Endpoint kombinasyon testi: Birden fazla şarj başlat/durdur döngüsü

        Senaryo:
        1. 3 kez şarj başlat/durdur döngüsü yap
        """
        ev_connected_data = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        charging_data = {
            "STATE": ESP32State.CHARGING.value,
            "AUTH": 1,
            "CABLE": 16,
        }

        for cycle in range(3):
            # Şarj başlat için EV_CONNECTED state
            mock_esp32_bridge.get_status.return_value = ev_connected_data

            response = client.post(
                "/api/charge/start",
                json={"user_id": f"test_user_{cycle}"},
                headers=test_headers,
            )
            assert response.status_code == 200, f"Cycle {cycle}: Charge start failed"

            # Şarj durdur için CHARGING state
            mock_esp32_bridge.get_status.return_value = charging_data

            response = client.post(
                "/api/charge/stop",
                json={},
                headers=test_headers,
            )
            assert response.status_code == 200, f"Cycle {cycle}: Charge stop failed"

    def test_current_set_during_charge_attempt(
        self, client, mock_esp32_bridge, test_headers
    ):
        """
        Endpoint kombinasyon testi: Şarj esnasında akım ayarlama denemesi

        Senaryo:
        1. Şarj başlat
        2. Şarj esnasında akım ayarlama denemesi (başarısız olmalı)
        """
        # 1. Şarj başlatma için EV_CONNECTED state
        ev_connected_data = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        mock_esp32_bridge.get_status.return_value = ev_connected_data

        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=test_headers,
        )
        assert response.status_code == 200

        # 2. Şarj esnasında akım ayarlama denemesi için CHARGING state
        charging_data = {
            "STATE": ESP32State.CHARGING.value,
            "AUTH": 1,
            "CABLE": 16,
            "MAX": 16,
        }
        mock_esp32_bridge.get_status.return_value = charging_data

        # 3. Şarj esnasında akım ayarlama denemesi (başarısız olmalı)
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20},
            headers=test_headers,
        )
        # Şarj esnasında akım ayarlama reddedilmeli
        assert response.status_code == 400
