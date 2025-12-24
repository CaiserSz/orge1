"""
API Endpoints Unit Tests
Created: 2025-12-09 02:00:00
Last Modified: 2025-12-24 21:21:42
Version: 1.1.5
Description: API endpoint'leri için unit testler - Mock ESP32 bridge ile
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import ESP32State

# conftest.py'den fixture'ları import et
# pytest otomatik olarak conftest.py'deki fixture'ları bulur
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


def _valid_meter_reading():
    return SimpleNamespace(
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


class _FakeMeter:
    def __init__(
        self, connected: bool, reading=None, read_exc: Exception | None = None
    ):
        self._connected = connected
        self._reading = reading
        self._read_exc = read_exc

    def is_connected(self):
        return self._connected

    def connect(self):
        return True

    def read_all(self):
        if self._read_exc:
            raise self._read_exc
        return self._reading


def _patch_get_meter(monkeypatch, value):
    import api.meter as meter_module

    monkeypatch.setattr(meter_module, "get_meter", lambda: value, raising=True)


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

    def test_esp32_logs_endpoint_reads_log_file(self, client, tmp_path, monkeypatch):
        """
        ESP32 log dosyasını API üzerinden okuyabiliyor muyuz?

        Not: Bu test gerçek logs/esp32.log dosyasına bağımlı değildir;
        tmp_path altında sahte bir log dosyası üretilip router içindeki
        ESP32_LOG_FILE değişkeni monkeypatch edilir.
        """
        fake_log = tmp_path / "esp32.log"
        fake_log.write_text(
            "\n".join(
                [
                    '{"timestamp":"2025-12-24T21:00:00","level":"INFO","logger":"esp32","type":"esp32_message","message_type":"status","direction":"rx","data":{"STATE":1}}',
                    '{"timestamp":"2025-12-24T21:00:01","level":"INFO","logger":"esp32","type":"esp32_message","message_type":"ack","direction":"rx","data":{"CMD":"AUTH","STATUS":"OK"}}',
                    '{"timestamp":"2025-12-24T21:00:02","level":"INFO","logger":"esp32","type":"esp32_message","message_type":"current_set","direction":"tx","data":{"amperage":16}}',
                ]
            ),
            encoding="utf-8",
        )

        from api.routers import status as status_router

        monkeypatch.setattr(status_router, "ESP32_LOG_FILE", fake_log, raising=True)

        res = client.get("/api/logs/esp32?lines=10&fmt=json")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["data"]["file"] == "esp32.log"
        assert body["data"]["lines_requested"] == 10
        assert body["data"]["format"] == "json"
        assert body["data"]["count"] == 3
        assert body["data"]["entries"][0]["message_type"] == "status"

        # Filtre: sadece TX current_set
        res2 = client.get(
            "/api/logs/esp32?lines=10&fmt=json&direction=tx&message_type=current_set"
        )
        assert res2.status_code == 200
        body2 = res2.json()
        assert body2["success"] is True
        assert body2["data"]["count"] == 1
        assert body2["data"]["entries"][0]["direction"] == "tx"
        assert body2["data"]["entries"][0]["message_type"] == "current_set"

        # Ham çıktı (raw)
        res3 = client.get(
            "/api/logs/esp32?lines=10&fmt=raw&direction=rx&message_type=status"
        )
        assert res3.status_code == 200
        body3 = res3.json()
        assert body3["success"] is True
        assert body3["data"]["format"] == "raw"
        assert body3["data"]["count"] == 1
        assert "message_type" in body3["data"]["entries"][0]

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

    @pytest.mark.parametrize("amperage", [8, 16, 24, 32])
    def test_set_current_valid(self, client, mock_esp32_bridge, test_headers, amperage):
        """Set current endpoint (valid values) çalışıyor mu?"""
        response = client.post(
            "/api/maxcurrent", json={"amperage": amperage}, headers=test_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert f"{amperage}A" in data["message"]
        mock_esp32_bridge.send_current_set.assert_called_once_with(amperage)

    @pytest.mark.parametrize("amperage", [5, 33])
    def test_set_current_invalid(self, client, amperage):
        """Geçersiz akım değerleri reddedilmeli."""
        response = client.post("/api/maxcurrent", json={"amperage": amperage})
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
    """Meter endpoint testleri (router seviyesinde, donanım/RS485 erişimi yok)."""

    def test_meter_status_when_module_returns_none(self, client, monkeypatch):
        _patch_get_meter(monkeypatch, None)

        res = client.get("/api/meter/status")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter modülü yüklü değil"
        assert body["data"]["connected"] is False
        assert body["data"]["available"] is False

    def test_meter_status_when_not_connected(self, client, monkeypatch):
        _patch_get_meter(monkeypatch, _FakeMeter(connected=False))

        res = client.get("/api/meter/status")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter bağlı değil"
        assert body["data"]["connected"] is False
        assert body["data"]["available"] is True

    def test_meter_status_when_connected_and_valid_reading(self, client, monkeypatch):
        _patch_get_meter(
            monkeypatch, _FakeMeter(connected=True, reading=_valid_meter_reading())
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
        _patch_get_meter(
            monkeypatch,
            _FakeMeter(connected=True, reading=SimpleNamespace(is_valid=False)),
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
        _patch_get_meter(
            monkeypatch,
            _FakeMeter(connected=True, read_exc=RuntimeError("read failed")),
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
        _patch_get_meter(monkeypatch, None)

        res = client.get("/api/meter/reading")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter modülü yüklü değil"
        assert body["data"] is None

    def test_meter_reading_when_not_connected(self, client, monkeypatch):
        _patch_get_meter(monkeypatch, _FakeMeter(connected=False))

        res = client.get("/api/meter/reading")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter bağlı değil"
        assert body["data"] is None

    def test_meter_reading_when_valid(self, client, monkeypatch):
        _patch_get_meter(
            monkeypatch, _FakeMeter(connected=True, reading=_valid_meter_reading())
        )

        res = client.get("/api/meter/reading")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter okuması başarıyla alındı"
        assert isinstance(body["data"], dict)
        assert body["data"]["energy_kwh"] == 100.5

    def test_meter_reading_when_invalid(self, client, monkeypatch):
        _patch_get_meter(
            monkeypatch,
            _FakeMeter(connected=True, reading=SimpleNamespace(is_valid=False)),
        )

        res = client.get("/api/meter/reading")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Meter verisi geçersiz"
        assert body["data"] is None


class TestMeterParsingHelpers:
    """Meter register decode / convert helper testleri (donanım/serial yok)."""

    def test_modbus_u32_from_regs(self):
        from api.meter.modbus import _u32_from_regs

        assert _u32_from_regs(0x0000, 0x0001) == 1
        assert _u32_from_regs(0x1234, 0x5678) == 0x12345678

    def test_modbus_s32_from_regs(self):
        from api.meter.modbus import _s32_from_regs

        assert _s32_from_regs(0x0000, 0x0001) == 1
        assert _s32_from_regs(0xFFFF, 0xFFFF) == -1

    def test_acrel_to_float(self):
        from api.meter.acrel import _to_float

        # IEEE754 1.0 -> 0x3F80 0x0000
        assert _to_float((0x3F80, 0x0000)) == pytest.approx(1.0)

    def test_acrel_to_float_invalid(self):
        from api.meter.acrel import _to_float

        assert _to_float((1,)) is None

    def test_acrel_read_uint32_scaled(self, monkeypatch):
        from api.meter.acrel import AcrelModbusMeter

        m = AcrelModbusMeter(port="dummy", baudrate=9600, slave_id=1, timeout=0.1)
        monkeypatch.setattr(m, "_read_regs", lambda address, count: (0x0000, 0x000A))

        # 10 * 0.1 = 1.0
        assert m._read_uint32_scaled(0x0842, 0.1) == pytest.approx(1.0)

    def test_acrel_read_uint32_scaled_none(self, monkeypatch):
        from api.meter.acrel import AcrelModbusMeter

        m = AcrelModbusMeter(port="dummy", baudrate=9600, slave_id=1, timeout=0.1)
        monkeypatch.setattr(m, "_read_regs", lambda address, count: None)

        assert m._read_uint32_scaled(0x0842, 0.1) is None


class TestABBMeterReadMeterHelpers:
    """meter/read_meter.py içindeki saf helper + Modbus frame logic testleri (donanım yok)."""

    def test_register_helpers(self):
        from meter.read_meter import _s32_from_2regs, _u32_from_2regs, _u64_from_4regs

        assert _u32_from_2regs(0x1234, 0x5678) == 0x12345678
        assert _s32_from_2regs(0xFFFF, 0xFFFF) == -1
        assert _u64_from_4regs([0, 0, 0, 1]) == 1
        with pytest.raises(ValueError):
            _u64_from_4regs([0, 1, 2])

    def test_crc_and_request_build(self):
        from meter.read_meter import ABBMeterReader

        r = ABBMeterReader(device="dummy", slave_id=1)
        payload = b"\x01\x03\x00\x00\x00\x0a"
        assert r._calculate_crc16(payload) == 0xCDC5
        assert r._build_modbus_request(0x03, 0x0000, 0x000A) == payload + b"\xc5\xcd"

    def test_parse_response_variants(self):
        import struct

        from meter.read_meter import ABBMeterReader

        r = ABBMeterReader(device="dummy", slave_id=1)
        data = b"\x12\x34\xab\xcd"
        pre = b"\x01\x03\x04" + data
        ok = pre + struct.pack("<H", r._calculate_crc16(pre))
        assert r._parse_modbus_response(ok) == [0x1234, 0xABCD]
        bad_crc = ok[:-1] + bytes([ok[-1] ^ 0xFF])
        assert r._parse_modbus_response(bad_crc) is None
        wrong_slave_pre = b"\x02\x03\x04" + data
        wrong_slave = wrong_slave_pre + struct.pack(
            "<H", r._calculate_crc16(wrong_slave_pre)
        )
        assert r._parse_modbus_response(wrong_slave) is None
        exc_pre = b"\x01\x83\x02"
        exc = exc_pre + struct.pack("<H", r._calculate_crc16(exc_pre))
        assert r._parse_modbus_response(exc) is None

    def test_read_meter_data_decoding_without_serial(self, monkeypatch):
        from meter.read_meter import ABB_REGISTERS, ABBMeterReader

        r = ABBMeterReader(device="dummy", slave_id=1)
        r.is_connected = True

        def fake_read(start_address: int, quantity: int):
            if (start_address, quantity) == (ABB_REGISTERS["voltage_l1"], 6):
                return [0, 230, 0, 231, 0, 232]
            if (start_address, quantity) == (ABB_REGISTERS["current_l1"], 6):
                return [0, 10_000, 0, 11_000, 0, 12_000]
            if (start_address, quantity) == (ABB_REGISTERS["power_active_total"], 8):
                return [0, 2300, 0, 700, 0, 800, 0, 900]
            if (start_address, quantity) == (ABB_REGISTERS["energy_active_import"], 4):
                return [0, 0, 0, 10_050]
            return None

        monkeypatch.setattr(r, "read_holding_registers", fake_read, raising=True)
        out = r.read_meter_data()
        assert out and out["slave_id"] == 1
        assert out["device"] == "dummy"
        assert out["voltage_l1"] == 230.0
        assert out["current_l1"] == pytest.approx(10.0)
        assert out["power_active_w"] == 2300.0
        assert out["energy_active_kwh"] == pytest.approx(100.5)
