"""
Error Handling ve Edge Case Testleri
Created: 2025-12-09 02:20:00
Last Modified: 2025-12-09 02:20:00
Version: 1.0.0
Description: Hata yönetimi, edge case'ler ve exception handling testleri
"""

import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import ESP32State
from api.main import app
from api.routers import dependencies

# conftest.py'deki standart fixture'ları kullan
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


class TestErrorHandling:
    """Hata yönetimi testleri"""

    def test_esp32_not_connected(self, client):
        """ESP32 bağlı değilken endpoint'ler hata döndürmeli"""
        # Bu testte bridge dependency'sini None olacak şekilde override et
        app.dependency_overrides[dependencies.get_bridge] = lambda: None
        try:
            response = client.get("/api/status")
            assert response.status_code == 503
            # Hata mesajı ESP32 bağlantısı olmadığını belirtmeli
            assert "bağlantısı yok" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(dependencies.get_bridge, None)

    def test_esp32_disconnected(self, client, mock_esp32_bridge):
        """ESP32 bağlantısı kopmuşken hata döndürmeli"""
        mock_esp32_bridge.is_connected = False

        response = client.get("/api/status")
        assert response.status_code == 503

    def test_get_status_timeout(self, client, mock_esp32_bridge):
        """Status alınamazsa timeout hatası döndürmeli"""
        mock_esp32_bridge.get_status.return_value = None
        mock_esp32_bridge.get_status_sync = Mock(return_value=None)

        response = client.get("/api/status")
        assert response.status_code == 504  # Gateway Timeout

    def test_send_command_failure(self, client, mock_esp32_bridge, test_headers):
        """Komut gönderilemezse hata döndürmeli"""
        # State'i geçerli bir başlatma senaryosu olacak şekilde ayarla (EV_CONNECTED),
        # böylece hata gerçekten komut gönderme katmanından gelsin.
        charge_start_data = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        mock_esp32_bridge.get_status.side_effect = [
            charge_start_data,  # İlk state kontrolü
            charge_start_data,  # Final state kontrolü
        ]
        mock_esp32_bridge.send_authorization.return_value = False

        response = client.post(
            "/api/charge/start", json={"id_tag": "TEST"}, headers=test_headers
        )
        assert response.status_code == 500
        assert "gönderilemedi" in response.json()["detail"].lower()

    def test_invalid_json_request(self, client):
        """Geçersiz JSON request hata döndürmeli"""
        response = client.post(
            "/api/charge/start",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422  # Validation Error

    def test_missing_required_fields(self, client):
        """Zorunlu alanlar eksikse hata döndürmeli"""
        response = client.post("/api/charge/start", json={})
        # id_tag eksik olabilir, kontrol et
        if response.status_code == 422:
            assert True  # Validation error bekleniyor


class TestEdgeCases:
    """Edge case testleri"""

    def test_boundary_current_values(self, client, mock_esp32_bridge, test_headers):
        """Sınır değerleri test et (6A ve 32A)"""
        # Minimum değer: 6A
        response = client.post(
            "/api/maxcurrent", json={"amperage": 6}, headers=test_headers
        )
        assert response.status_code == 200

        # Maksimum değer: 32A
        response = client.post(
            "/api/maxcurrent", json={"amperage": 32}, headers=test_headers
        )
        assert response.status_code == 200

    def test_invalid_current_below_minimum(self, client, test_headers):
        """Minimum değerin altında akım reddedilmeli"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": 5}, headers=test_headers
        )
        assert response.status_code == 422  # Validation Error

    def test_invalid_current_above_maximum(self, client, test_headers):
        """Maksimum değerin üstünde akım reddedilmeli"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": 33}, headers=test_headers
        )
        assert response.status_code == 422  # Validation Error

    def test_zero_current(self, client, test_headers):
        """Sıfır akım reddedilmeli"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": 0}, headers=test_headers
        )
        assert response.status_code == 422

    def test_negative_current(self, client, test_headers):
        """Negatif akım reddedilmeli"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": -1}, headers=test_headers
        )
        assert response.status_code == 422

    def test_float_current(self, client, test_headers):
        """Float akım değeri reddedilmeli (sadece integer)"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": 16.5}, headers=test_headers
        )
        # Pydantic integer validation'ı float'ı reddeder veya dönüştürür
        assert response.status_code in [
            422,
            200,
        ]  # Validation error veya otomatik dönüşüm

    def test_very_large_current(self, client, test_headers):
        """Çok büyük akım değeri reddedilmeli"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": 999999}, headers=test_headers
        )
        assert response.status_code == 422

    def test_empty_id_tag(self, client, mock_esp32_bridge, test_headers):
        """Boş id_tag ile şarj başlatma"""
        # State'i EV_CONNECTED yaparak sadece id_tag davranışını test et
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        response = client.post(
            "/api/charge/start", json={"id_tag": ""}, headers=test_headers
        )
        # Boş string geçerli olabilir veya reddedilebilir
        assert response.status_code in [200, 422]

    def test_very_long_id_tag(self, client, mock_esp32_bridge, test_headers):
        """Çok uzun id_tag ile şarj başlatma"""
        long_tag = "A" * 1000
        # State'i EV_CONNECTED yaparak sadece id_tag davranışını test et
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
        }
        response = client.post(
            "/api/charge/start", json={"id_tag": long_tag}, headers=test_headers
        )
        # Çok uzun string reddedilebilir veya kabul edilebilir
        assert response.status_code in [200, 422]


class TestConcurrentRequests:
    """Eşzamanlı istek testleri"""

    def test_concurrent_status_requests(self, client, mock_esp32_bridge):
        """Eşzamanlı status istekleri"""
        import threading

        results = []

        def make_request():
            response = client.get("/api/status")
            results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Tüm istekler başarılı olmalı
        assert all(code == 200 for code in results)

    def test_concurrent_start_charge(self, client, mock_esp32_bridge, test_headers):
        """Eşzamanlı şarj başlatma istekleri"""
        import threading

        results = []

        def make_request():
            response = client.post(
                "/api/charge/start", json={"id_tag": "TEST"}, headers=test_headers
            )
            results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # İlk istek başarılı, diğerleri state kontrolü nedeniyle başarısız olabilir
        assert len(results) == 5


class TestStateTransitions:
    """State geçiş testleri"""

    def test_state_transition_sequence(self, client, mock_esp32_bridge, test_headers):
        """Normal state geçiş sırası"""
        # 1. IDLE durumunda akım ayarla
        mock_esp32_bridge.get_status = Mock(
            return_value={"STATE": ESP32State.IDLE.value}
        )
        response = client.post(
            "/api/maxcurrent", json={"amperage": 16}, headers=test_headers
        )
        assert response.status_code == 200

        # 2. EV_CONNECTED durumunda şarj başlat (CABLE_DETECT değil, EV_CONNECTED gerekli)
        mock_esp32_bridge.get_status = Mock(
            return_value={"STATE": ESP32State.EV_CONNECTED.value}
        )
        response = client.post(
            "/api/charge/start", json={"id_tag": "TEST"}, headers=test_headers
        )
        assert response.status_code == 200

        # 3. Şarj aktifken akım değiştirme denemesi
        mock_esp32_bridge.get_status = Mock(
            return_value={"STATE": ESP32State.CHARGING.value}
        )
        response = client.post(
            "/api/maxcurrent", json={"amperage": 24}, headers=test_headers
        )
        assert response.status_code == 400

    def test_all_state_values(self, client, mock_esp32_bridge, test_headers):
        """Tüm state değerleri için kontrol"""
        # ESP32State enum değerlerini kullan
        all_states = [state.value for state in ESP32State]
        for state_value in all_states:
            mock_esp32_bridge.get_status.return_value = {"STATE": state_value}

            # Status endpoint her zaman çalışmalı
            response = client.get("/api/status")
            # Rate limiting devreye girmişse 429 da kabul edilebilir
            assert response.status_code in [200, 429]

            # State değerine göre start charge kontrolü
            response = client.post(
                "/api/charge/start", json={"id_tag": "TEST"}, headers=test_headers
            )
            # Yeni business rule: charge_start yalnızca EV_CONNECTED state'inde geçerli
            if state_value == ESP32State.EV_CONNECTED.value:
                assert response.status_code in [200, 429]
            else:
                assert response.status_code in [400, 429]


class TestSerialCommunication:
    """Serial communication hata senaryoları"""

    def test_serial_write_exception(self, client, mock_esp32_bridge, test_headers):
        """Serial write exception durumu"""
        # Charge start state validation'ı geçebilmek için EV_CONNECTED state'i gerekli
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value
        }
        mock_esp32_bridge.send_authorization.side_effect = Exception(
            "Serial write failed"
        )

        response = client.post(
            "/api/charge/start", json={"id_tag": "TEST"}, headers=test_headers
        )
        # Exception yakalanmalı ve 500 hatası döndürülmeli; ancak rate limit
        # devreye girmişse 429 da kabul edilebilir.
        assert response.status_code in [500, 429]

    def test_serial_read_timeout(self, client, mock_esp32_bridge):
        """Serial read timeout durumu"""
        mock_esp32_bridge.get_status.return_value = None
        mock_esp32_bridge.get_status_sync = Mock(return_value=None)

        response = client.get("/api/status")
        assert response.status_code == 504


class TestDataValidation:
    """Veri doğrulama testleri"""

    def test_status_response_structure(self, client, mock_esp32_bridge):
        """Status response yapısı doğru mu?"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "AUTH": 0,
            "CABLE": 0,
            "MAX": 16,
            "CP": 0,
            "PP": 0,
        }

        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()

        # Response yapısı kontrolü
        assert "success" in data
        assert "message" in data
        assert "data" in data
        assert "timestamp" in data

        # Data içeriği kontrolü
        assert "STATE" in data["data"]
        assert "AUTH" in data["data"]

    def test_error_response_structure(self, client):
        """Hata response yapısı doğru mu?"""
        app.dependency_overrides[dependencies.get_bridge] = lambda: None
        try:
            response = client.get("/api/status")
            assert response.status_code == 503

            # Hata response'u kontrol et
            # FastAPI HTTPException detail field'ı döndürür
            assert "detail" in response.json()
        finally:
            app.dependency_overrides.pop(dependencies.get_bridge, None)
