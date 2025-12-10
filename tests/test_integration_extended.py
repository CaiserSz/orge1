"""
Extended Integration Tests
Created: 2025-12-09 23:55:00
Last Modified: 2025-12-09 23:55:00
Version: 1.0.0
Description: Genişletilmiş integration testleri - gerçek senaryolar
"""

import sys
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import ESP32State


# conftest.py'deki standart fixture'ları kullan
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


class TestCompleteChargingWorkflow:
    """Tam şarj workflow testleri"""

    def test_complete_charging_workflow_idle_to_charging(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Tam şarj workflow - IDLE'dan CHARGING'e"""
        # 1. Başlangıç durumu: IDLE
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }

        # 2. Akım ayarla
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200

        # 3. State değiş: CABLE_DETECT
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CABLE_DETECT.value,
            "MAX": 16,
        }

        # 4. Şarj başlat
        response = client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200

        # 5. State değiş: CHARGING
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CHARGING.value,
            "MAX": 16,
        }

        # 6. Status kontrol et
        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["data"]["STATE"] == ESP32State.CHARGING.value

        # 7. Şarj durdur
        response = client.post(
            "/api/charge/stop", json={}, headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200

        # 8. State değiş: IDLE
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }

        # 9. Final status kontrol
        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["data"]["STATE"] == ESP32State.IDLE.value

    def test_charging_workflow_with_multiple_current_changes(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Şarj workflow - birden fazla akım değişikliği"""
        # 1. İlk akım ayarla
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 10},
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200

        # 2. Akım değiştir
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20},
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200

        # 3. Son akım ayarla
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200

        # Tüm akım değişiklikleri başarılı olmalı
        assert mock_esp32_bridge.send_current_set.call_count == 3

    def test_charging_workflow_error_recovery(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Şarj workflow - hata kurtarma"""
        # 1. Şarj başlatma denemesi - başarısız komut
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }
        mock_esp32_bridge.send_authorization.return_value = False

        response = client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 500

        # 2. Komut başarılı olana kadar tekrar dene
        mock_esp32_bridge.send_authorization.return_value = True
        response = client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200


class TestConcurrentOperations:
    """Eşzamanlı operasyon testleri"""

    def test_concurrent_status_requests(self, client, mock_esp32_bridge):
        """Eşzamanlı status istekleri"""
        import threading

        results = []

        def get_status():
            response = client.get("/api/status")
            results.append(response.status_code)

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_status)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Tüm istekler başarılı olmalı
        assert all(status == 200 for status in results)
        assert len(results) == 10

    def test_concurrent_current_set_requests(
        self, client, mock_esp32_bridge, test_headers
    ):
        """Eşzamanlı akım ayarlama istekleri"""
        import threading

        results = []

        def set_current(amperage):
            response = client.post(
                "/api/maxcurrent",
                json={"amperage": amperage},
                headers={"X-API-Key": "test-api-key"},
            )
            results.append(response.status_code)

        threads = []
        amperages = [6, 10, 13, 16, 20, 25, 32]
        for amp in amperages:
            thread = threading.Thread(target=set_current, args=(amp,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Tüm istekler başarılı olmalı (state kontrolü yapıldığı için)
        assert all(status == 200 for status in results)
        assert len(results) == len(amperages)


class TestStateTransitionScenarios:
    """State transition senaryoları"""

    def test_all_valid_state_transitions(self, client, mock_esp32_bridge, test_headers):
        """Tüm geçerli state transition'ları"""
        valid_transitions = [
            (
                ESP32State.IDLE.value,
                ESP32State.CABLE_DETECT.value,
            ),  # IDLE -> CABLE_DETECT
            (
                ESP32State.CABLE_DETECT.value,
                ESP32State.EV_CONNECTED.value,
            ),  # CABLE_DETECT -> EV_CONNECTED
            (
                ESP32State.EV_CONNECTED.value,
                ESP32State.READY.value,
            ),  # EV_CONNECTED -> READY
            (ESP32State.READY.value, ESP32State.CHARGING.value),  # READY -> CHARGING
            (ESP32State.CHARGING.value, ESP32State.PAUSED.value),  # CHARGING -> PAUSED
            (ESP32State.PAUSED.value, ESP32State.CHARGING.value),  # PAUSED -> CHARGING
            (
                ESP32State.CHARGING.value,
                ESP32State.STOPPED.value,
            ),  # CHARGING -> STOPPED
            (ESP32State.STOPPED.value, ESP32State.IDLE.value),  # STOPPED -> IDLE
        ]

        for from_state, to_state in valid_transitions:
            mock_esp32_bridge.get_status.return_value = {"STATE": from_state, "MAX": 16}

            # State transition'ı simüle et
            if to_state == ESP32State.CHARGING.value:  # CHARGING
                response = client.post(
                    "/api/charge/start", json={}, headers={"X-API-Key": "test-api-key"}
                )
                # State IDLE-READY arası ise başarılı olmalı
                if from_state < ESP32State.CHARGING.value:
                    assert response.status_code == 200
            elif (
                from_state == ESP32State.CHARGING.value
                and to_state == ESP32State.STOPPED.value
            ):  # CHARGING -> STOPPED
                response = client.post(
                    "/api/charge/stop", json={}, headers={"X-API-Key": "test-api-key"}
                )
                assert response.status_code == 200

    def test_invalid_state_transitions(self, client, mock_esp32_bridge, test_headers):
        """Geçersiz state transition'ları"""
        # CHARGING durumunda şarj başlatma denemesi
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CHARGING.value,
            "MAX": 16,
        }

        response = client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 400

        # CHARGING durumunda akım değiştirme denemesi
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 20},
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 400


class TestAPIResponseConsistency:
    """API response tutarlılık testleri"""

    def test_all_endpoints_return_consistent_format(self, client, mock_esp32_bridge):
        """Tüm endpoint'ler tutarlı format döndürüyor mu?"""
        endpoints = [
            ("GET", "/api/health"),
            ("GET", "/api/status"),
            ("GET", "/api/current/available"),
            ("GET", "/api/station/info"),
        ]

        for method, path in endpoints:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path, json={})

            if response.status_code == 200:
                data = response.json()
                # APIResponse format kontrolü
                assert "success" in data
                assert isinstance(data["success"], bool)
                assert "message" in data
                assert "data" in data

    def test_error_responses_consistent_format(self, client, mock_esp32_bridge):
        """Hata response'ları tutarlı format döndürüyor mu?"""
        # 404 hatası
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

        # 401 hatası (API key yok)
        response = client.post("/api/charge/start", json={})
        assert response.status_code == 401

        # 422 hatası (validation error) - API key ile
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 5},  # Geçersiz değer
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 422


class TestStationInfoWorkflow:
    """Station info workflow testleri"""

    def test_station_info_save_and_retrieve(self, client):
        """Station info kaydetme ve alma workflow'u"""
        test_data = {
            "station_id": "TEST-001",
            "name": "Test Station",
            "location": "Test Location",
            "max_current": 32,
        }

        # 1. Station info kaydet
        with patch("api.main.save_station_info", return_value=True):
            response = client.post("/api/station/info", json=test_data)
            assert response.status_code == 200

        # 2. Station info al
        with patch("api.main.get_station_info", return_value=test_data):
            response = client.get("/api/station/info")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["station_id"] == "TEST-001"
            assert data["data"]["name"] == "Test Station"

    def test_station_info_not_found_flow(self, client):
        """Station info bulunamadığında workflow"""
        # Station info yok
        with patch("api.main.get_station_info", return_value=None):
            response = client.get("/api/station/info")
            assert response.status_code == 404
            assert "bulunamadı" in response.json()["detail"]
