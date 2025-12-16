"""
API Endpoints Unit Tests
Created: 2025-12-09 02:00:00
Last Modified: 2025-12-16 09:40:00
Version: 1.1.0
Description: API endpoint'leri için unit testler - Mock ESP32 bridge ile
"""

import sys
from pathlib import Path
from types import SimpleNamespace

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


class TestMeterEndpoints:
    """
    Meter endpoint testleri (router seviyesinde)

    Not:
      Bu testler donanım/RS485 erişimi yapmaz; `api.meter.get_meter` patch edilerek
      router'ın tüm branch'leri güvenli şekilde kapsanır.
    """

    def test_meter_status_when_module_returns_none(self, client, monkeypatch):
        import api.meter as meter_module

        monkeypatch.setattr(meter_module, "get_meter", lambda: None, raising=True)

        res = client.get("/api/meter/status")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter modülü yüklü değil"
        assert body["data"]["connected"] is False
        assert body["data"]["available"] is False

    def test_meter_status_when_not_connected(self, client, monkeypatch):
        import api.meter as meter_module

        class FakeMeter:
            def is_connected(self):
                return False

            def connect(self):
                return True

        monkeypatch.setattr(
            meter_module, "get_meter", lambda: FakeMeter(), raising=True
        )

        res = client.get("/api/meter/status")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter bağlı değil"
        assert body["data"]["connected"] is False
        assert body["data"]["available"] is True

    def test_meter_status_when_connected_and_valid_reading(self, client, monkeypatch):
        import api.meter as meter_module

        reading = SimpleNamespace(
            is_valid=True,
            voltage_v=230.0,
            current_a=10.0,
            power_w=2300.0,
            power_kw=2.3,
            energy_kwh=100.5,
            frequency_hz=50.0,
            power_factor=0.98,
            timestamp="2025-12-16T09:40:00Z",
            phase_values={"l1": {"v": 230.0}},
            totals={"energy_import_kwh": 100.5},
        )

        class FakeMeter:
            def is_connected(self):
                return True

            def read_all(self):
                return reading

        monkeypatch.setattr(
            meter_module, "get_meter", lambda: FakeMeter(), raising=True
        )

        res = client.get("/api/meter/status")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter verileri başarıyla alındı"
        assert body["data"]["connected"] is True
        assert body["data"]["available"] is True
        assert body["data"]["voltage_v"] == 230.0
        assert body["data"]["energy_kwh"] == 100.5

    def test_meter_status_when_connected_but_invalid_reading(self, client, monkeypatch):
        import api.meter as meter_module

        reading = SimpleNamespace(is_valid=False)

        class FakeMeter:
            def is_connected(self):
                return True

            def read_all(self):
                return reading

        monkeypatch.setattr(
            meter_module, "get_meter", lambda: FakeMeter(), raising=True
        )

        res = client.get("/api/meter/status")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter verisi geçersiz"
        assert body["data"]["connected"] is True
        assert body["data"]["available"] is True
        assert body["data"]["valid"] is False

    def test_meter_status_when_read_raises_exception(self, client, monkeypatch):
        import api.meter as meter_module

        class FakeMeter:
            def is_connected(self):
                return True

            def read_all(self):
                raise RuntimeError("read failed")

        monkeypatch.setattr(
            meter_module, "get_meter", lambda: FakeMeter(), raising=True
        )

        res = client.get("/api/meter/status")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter verisi okunamadı"
        assert body["data"]["connected"] is True
        assert body["data"]["available"] is True
        assert "read failed" in body["data"]["error"]

    def test_meter_reading_when_module_returns_none(self, client, monkeypatch):
        import api.meter as meter_module

        monkeypatch.setattr(meter_module, "get_meter", lambda: None, raising=True)

        res = client.get("/api/meter/reading")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter modülü yüklü değil"
        assert body["data"] is None

    def test_meter_reading_when_not_connected(self, client, monkeypatch):
        import api.meter as meter_module

        class FakeMeter:
            def is_connected(self):
                return False

            def connect(self):
                return True

        monkeypatch.setattr(
            meter_module, "get_meter", lambda: FakeMeter(), raising=True
        )

        res = client.get("/api/meter/reading")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter bağlı değil"
        assert body["data"] is None

    def test_meter_reading_when_valid(self, client, monkeypatch):
        import api.meter as meter_module

        reading = SimpleNamespace(
            is_valid=True,
            voltage_v=230.0,
            current_a=10.0,
            power_w=2300.0,
            power_kw=2.3,
            energy_kwh=100.5,
            frequency_hz=50.0,
            power_factor=0.98,
            timestamp="2025-12-16T09:40:00Z",
            phase_values={"l1": {"v": 230.0}},
            totals={"energy_import_kwh": 100.5},
        )

        class FakeMeter:
            def is_connected(self):
                return True

            def read_all(self):
                return reading

        monkeypatch.setattr(
            meter_module, "get_meter", lambda: FakeMeter(), raising=True
        )

        res = client.get("/api/meter/reading")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter okuması başarıyla alındı"
        assert isinstance(body["data"], dict)
        assert body["data"]["energy_kwh"] == 100.5

    def test_meter_reading_when_invalid(self, client, monkeypatch):
        import api.meter as meter_module

        reading = SimpleNamespace(is_valid=False)

        class FakeMeter:
            def is_connected(self):
                return True

            def read_all(self):
                return reading

        monkeypatch.setattr(
            meter_module, "get_meter", lambda: FakeMeter(), raising=True
        )

        res = client.get("/api/meter/reading")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter verisi geçersiz"
        assert body["data"] is None
