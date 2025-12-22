"""
Protocol Rule Tests
Created: 2025-12-13 02:40:00
Last Modified: 2025-12-22 06:30:58
Version: 1.1.1
Description: ESP32 protokol kuralları ve edge case testleri.
"""

import asyncio
import base64
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parent.parent


def _load_protocol_json() -> dict:
    protocol_path = ROOT / "esp32" / "protocol.json"
    with open(protocol_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestProtocolRules:
    @pytest.fixture
    def rules(self):
        return _load_protocol_json().get("rules", {})

    def test_rules_exist(self, rules):
        assert len(rules) > 0, "rules bölümü boş"

    @pytest.mark.parametrize(
        "rule_key",
        (
            "current_set_only_before_charging",
            "only_defined_commands",
            "current_set_range",
        ),
    )
    def test_rule_key_exists(self, rules, rule_key):
        assert rule_key in rules, f"{rule_key} kuralı bulunamadı"

    def test_current_set_range_mentions_6_32(self, rules):
        rule_text = rules["current_set_range"]
        assert (
            "6-32" in rule_text
        ), "current_set_range kuralı 6-32 aralığını belirtmiyor"


class TestProtocolEdgeCases:
    @pytest.fixture
    def protocol_data(self):
        return _load_protocol_json()

    def test_no_duplicate_command_ids(self, protocol_data):
        commands = protocol_data.get("commands", {})
        id_value_pairs = {}
        for cmd_name, cmd_data in commands.items():
            cmd_id = cmd_data.get("id")
            cmd_value = cmd_data.get("value")
            pair = (cmd_id, cmd_value)
            if pair in id_value_pairs:
                if not cmd_name.startswith("current_set_"):
                    pytest.fail(
                        f"{cmd_name} ve {id_value_pairs[pair]} aynı ID ve value'ya sahip"
                    )
            else:
                id_value_pairs[pair] = cmd_name

    def test_commands_fields_valid(self, protocol_data):
        commands = protocol_data.get("commands", {})
        valid_categories = {"status", "charge_control", "current_set"}
        for cmd_name, cmd_data in commands.items():
            category = cmd_data.get("category", "")
            assert (
                category in valid_categories
            ), f"{cmd_name} geçersiz category: {category}"

            hex_str = cmd_data.get("hex", "")
            if not hex_str:
                continue

            for hex_byte in hex_str.split():
                try:
                    int(hex_byte, 16)
                except ValueError:
                    pytest.fail(f"{cmd_name} komutunda geçersiz hex değer: {hex_byte}")

            byte_array = cmd_data.get("byte_array", [])
            if byte_array:
                assert byte_array == [
                    int(b, 16) for b in hex_str.split()
                ], f"{cmd_name} byte_array hex ile eşleşmiyor"


def _load_module_from_path(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestOcppStateHelpers:
    @pytest.fixture
    def ocpp_states(self):
        return _load_module_from_path("ocpp_states", ROOT / "ocpp" / "states.py")

    def test_basic_auth_header_roundtrip(self, ocpp_states):
        header = ocpp_states.basic_auth_header("station", "secret")
        assert header.startswith("Basic ")
        token = header.split(" ", 1)[1]
        raw = base64.b64decode(token.encode("ascii")).decode("utf-8")
        assert raw == "station:secret"

    def test_ssl_if_needed(self, ocpp_states):
        assert ocpp_states.ssl_if_needed("ws://example.com") is None
        ctx = ocpp_states.ssl_if_needed("wss://example.com")
        assert ctx is not None

    @pytest.mark.parametrize(
        ("value", "expected"), [(None, None), ("12.5", 12.5), (3, 3.0), ("nope", None)]
    )
    def test_safe_float(self, ocpp_states, value, expected):
        assert ocpp_states.safe_float(value) == expected

    @pytest.mark.parametrize(
        ("name", "expected"),
        [("", "UNKNOWN"), ("   ", "UNKNOWN"), ("ORGE_AC_001", "ORGE_AC_001")],
    )
    def test_serial_number_for_station_name(self, ocpp_states, name, expected):
        assert ocpp_states.serial_number_for_station_name(name) == expected
        long_name = "X" * 100
        assert len(ocpp_states.serial_number_for_station_name(long_name)) == 25

    @pytest.mark.parametrize(
        ("state_name", "availability", "expected"),
        [
            ("IDLE", None, "available"),
            ("CHARGING", None, "occupied"),
            ("READY", None, "reserved"),
            ("FAULT_HARD", None, "faulted"),
            (None, "busy", "occupied"),
            ("UNKNOWN", "available", "available"),
            ("UNKNOWN", "something", "unavailable"),
        ],
    )
    def test_derive_connector_status_label(
        self, ocpp_states, state_name, availability, expected
    ):
        def _payload():
            return {
                "data": {
                    "status": {"state_name": state_name, "availability": availability}
                }
            }

        assert (
            ocpp_states.derive_connector_status_label_from_station_payload(_payload())
            == expected
        )

    def test_derive_connector_status_label_none(self, ocpp_states):
        assert (
            ocpp_states.derive_connector_status_label_from_station_payload(None) is None
        )

    @pytest.mark.parametrize(
        ("payload", "expected"),
        [
            (None, None),
            ({"data": {"totals": {"energy_import_kwh": 10.25}}}, 10.25),
            ({"data": {"totals": {"energy_kwh": "9.0"}}}, 9.0),
            ({"data": {"energy_kwh": 7}}, 7.0),
        ],
    )
    def test_extract_energy_import_kwh(self, ocpp_states, payload, expected):
        assert (
            ocpp_states.extract_energy_import_kwh_from_meter_payload(payload)
            == expected
        )

    @pytest.mark.parametrize(
        ("payload", "expected"),
        [
            (None, None),
            ({"session": None}, None),
            (
                {"session": {"session_id": "S1", "status": "ACTIVE"}},
                {"session_id": "S1", "status": "ACTIVE"},
            ),
        ],
    )
    def test_extract_current_session(self, ocpp_states, payload, expected):
        assert (
            ocpp_states.extract_current_session_from_sessions_current_payload(payload)
            == expected
        )

    def test_http_get_json_sync_success_and_error(self, ocpp_states, monkeypatch):
        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"ok": true}'

        def fake_urlopen(req, timeout):
            assert timeout == 0.1
            return FakeResp()

        monkeypatch.setattr(
            ocpp_states.urllib.request, "urlopen", fake_urlopen, raising=True
        )
        assert ocpp_states._http_get_json_sync("http://x", timeout_seconds=0.1) == {
            "ok": True
        }

        def fake_urlopen_error(req, timeout):
            raise ocpp_states.urllib.error.URLError("boom")

        monkeypatch.setattr(
            ocpp_states.urllib.request, "urlopen", fake_urlopen_error, raising=True
        )
        assert ocpp_states._http_get_json_sync("http://x", timeout_seconds=0.1) is None

    @pytest.mark.asyncio
    async def test_local_api_poller_transitions(self, ocpp_states, monkeypatch):
        events = {"status": [], "energy": [], "started": [], "ended": []}

        async def on_status_change(label: str):
            events["status"].append(label)

        async def on_energy_update(kwh: float):
            events["energy"].append(kwh)

        async def on_session_started(session_id: str, energy_kwh):
            events["started"].append((session_id, energy_kwh))

        async def on_session_ended(session_id: str, energy_kwh, old_status):
            events["ended"].append((session_id, energy_kwh, old_status))

        responses = [
            {
                "data": {
                    "status": {"state_name": "CHARGING", "availability": "available"}
                }
            },
            {"data": {"totals": {"energy_import_kwh": 1.0}}},
            {"session": {"session_id": "S1", "status": "ACTIVE"}},
            {"data": {"status": {"state_name": "IDLE", "availability": "available"}}},
            {"data": {"totals": {"energy_import_kwh": 0.5}}},
            {"session": None},
        ]

        async def fake_http_get_json(url: str, timeout_seconds: float = 2.0):
            assert "http://localhost:8000" in url
            return responses.pop(0)

        monkeypatch.setattr(
            ocpp_states, "http_get_json", fake_http_get_json, raising=True
        )

        sleep_calls = {"n": 0}

        async def fake_sleep(seconds: float):
            sleep_calls["n"] += 1
            if sleep_calls["n"] >= 2:
                raise asyncio.CancelledError()
            return None

        monkeypatch.setattr(ocpp_states.asyncio, "sleep", fake_sleep, raising=True)

        poller = ocpp_states.LocalApiPoller(
            ocpp_states.LocalApiPollerConfig(
                base_url="http://localhost:8000/", poll_interval_seconds=1
            )
        )
        # clamp check
        assert poller.cfg.base_url == "http://localhost:8000"
        assert poller.cfg.poll_interval_seconds == 5

        with pytest.raises(asyncio.CancelledError):
            await poller.run(
                on_status_change=on_status_change,
                on_energy_update=on_energy_update,
                on_session_started=on_session_started,
                on_session_ended=on_session_ended,
            )

        assert events["status"] == ["occupied", "available"]
        assert events["energy"] == [1.0]
        assert events["started"] == [("S1", 1.0)]
        assert events["ended"] == [("S1", 1.0, "ACTIVE")]

    @pytest.mark.asyncio
    async def test_local_api_poller_swallow_errors(self, ocpp_states, monkeypatch):
        async def fake_http_get_json(url: str, timeout_seconds: float = 2.0):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            ocpp_states, "http_get_json", fake_http_get_json, raising=True
        )

        async def fake_sleep(seconds: float):
            raise asyncio.CancelledError()

        monkeypatch.setattr(ocpp_states.asyncio, "sleep", fake_sleep, raising=True)

        poller = ocpp_states.LocalApiPoller(
            ocpp_states.LocalApiPollerConfig(
                base_url="http://localhost:8000", poll_interval_seconds=10
            )
        )

        with pytest.raises(asyncio.CancelledError):
            await poller.run(
                on_status_change=lambda *_: asyncio.sleep(0),
                on_energy_update=lambda *_: asyncio.sleep(0),
                on_session_started=lambda *_: asyncio.sleep(0),
                on_session_ended=lambda *_: asyncio.sleep(0),
            )


class TestOcppRunnerHelpers:
    @pytest.fixture
    def ocpp_states_as_package_name(self):
        # handlers.py ve main.py, `states` ismiyle import bekliyor
        return _load_module_from_path("states", ROOT / "ocpp" / "states.py")

    @pytest.fixture
    def ocpp_handlers(self, ocpp_states_as_package_name):
        return _load_module_from_path("handlers", ROOT / "ocpp" / "handlers.py")

    @pytest.fixture
    def ocpp_main(self, ocpp_handlers, ocpp_states_as_package_name):
        return _load_module_from_path("ocpp_main", ROOT / "ocpp" / "main.py")

    def test_handlers_retryable_error(self, ocpp_handlers):
        assert ocpp_handlers._is_retryable_ws_error(RuntimeError("x")) is True
        assert ocpp_handlers._is_retryable_ws_error(Exception("x")) is True
        assert ocpp_handlers._is_retryable_ws_error(KeyboardInterrupt()) is False

    @pytest.mark.asyncio
    async def test_handlers_sleep_backoff_caps(self, ocpp_handlers, monkeypatch):
        delays = []

        async def fake_sleep(seconds: float):
            delays.append(seconds)
            return None

        monkeypatch.setattr(ocpp_handlers.asyncio, "sleep", fake_sleep, raising=True)

        await ocpp_handlers._sleep_backoff(attempt=0)
        await ocpp_handlers._sleep_backoff(attempt=3)
        await ocpp_handlers._sleep_backoff(attempt=10)
        assert delays == [1.0, 8.0, 30.0]

    def test_main_parse_bool(self, ocpp_main):
        assert ocpp_main._parse_bool("true", default=False) is True
        assert ocpp_main._parse_bool("0", default=True) is False
        assert ocpp_main._parse_bool("weird", default=True) is True
        assert ocpp_main._parse_bool("", default=False) is False

    def test_main_build_config_primary_validation(self, ocpp_main):
        import argparse

        args = argparse.Namespace(
            station_name="S",
            station_password="P",
            ocpp201_url="wss://example/ocpp/S",
            ocpp16_url="wss://example/ocpp16/S",
            primary="201",
            poc=False,
            once=True,
            vendor_name="V",
            model="M",
            id_token="TEST001",
            heartbeat_seconds=0,
            local_api_base_url="http://localhost:8000",
            local_poll_enabled="true",
            local_poll_interval_seconds=10,
        )

        cfg = ocpp_main._build_config(args)
        assert cfg.primary == "201"
        assert cfg.station_name == "S"
        assert cfg.local_api_base_url == "http://localhost:8000"

        args_bad = argparse.Namespace(**{**args.__dict__, "primary": "bad"})
        with pytest.raises(ValueError):
            ocpp_main._build_config(args_bad)
