"""
Integration Testleri - Gerçek Senaryolar
Created: 2025-12-09 02:25:00
Last Modified: 2025-12-21 17:05:00
Version: 1.1.1
Description: Gerçek kullanım senaryoları ve integration testleri (API + OCPP Remote Ops)
"""

import asyncio
import base64
import contextlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import ESP32State

# conftest.py'deki standart fixture'ları kullan
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


class TestRealWorldScenarios:
    """Gerçek dünya senaryoları"""

    def test_complete_charging_flow(self, client, mock_esp32_bridge):
        """Tam şarj akışı senaryosu"""
        # 1. Durum kontrolü
        response = client.get("/api/status")
        assert response.status_code == 200

        # 2. Akım ayarlama
        mock_esp32_bridge.get_status.return_value = {"STATE": 1}
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        assert response.status_code == 200

        # 3. Kablo takıldı (STATE=2)
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CABLE_DETECT.value,
            "PP": 1,
            "CABLE": 32,
        }
        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["data"]["STATE"] == 2

        # 4. Araç bağlandı (STATE=3)
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "CP": 1,
        }
        response = client.get("/api/status")
        assert response.status_code == 200

        # 5. Şarj başlatma
        response = client.post("/api/charge/start", json={"id_tag": "TEST-001"})
        assert response.status_code == 200

        # 6. Şarj aktif (STATE=5)
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.CHARGING.value,
            "AUTH": 1,
            "CABLE": 16,
        }
        response = client.get("/api/status")
        assert response.status_code == 200

        # 7. Şarj durdurma
        response = client.post("/api/charge/stop", json={})
        assert response.status_code == 200

        # 8. Şarj bitirildi (STATE=7)
        mock_esp32_bridge.get_status.return_value = {"STATE": ESP32State.STOPPED.value}
        response = client.get("/api/status")
        assert response.status_code == 200

    def test_multiple_current_changes(self, client, mock_esp32_bridge):
        """Birden fazla akım değişikliği"""
        mock_esp32_bridge.get_status.return_value = {"STATE": 1}

        # 8A ayarla
        response = client.post("/api/maxcurrent", json={"amperage": 8})
        assert response.status_code == 200

        # 16A ayarla
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        assert response.status_code == 200

        # 24A ayarla
        response = client.post("/api/maxcurrent", json={"amperage": 24})
        assert response.status_code == 200

        # 32A ayarla
        response = client.post("/api/maxcurrent", json={"amperage": 32})
        assert response.status_code == 200

    def test_charging_with_different_currents(self, client, mock_esp32_bridge):
        """Farklı akımlarla şarj başlatma"""
        currents = [8, 16, 24, 32]

        for current in currents:
            # Akım ayarla
            mock_esp32_bridge.get_status.return_value = {"STATE": 1}
            response = client.post("/api/maxcurrent", json={"amperage": current})
            assert response.status_code == 200

            # Şarj başlat
            # Charge start yalnızca EV_CONNECTED (3) state'inde geçerli.
            # Ayrıca charge_start içinde iki kez get_status çağrısı var (ilk + final kontrol).
            mock_esp32_bridge.get_status.side_effect = None
            mock_esp32_bridge.get_status.return_value = {
                "STATE": ESP32State.EV_CONNECTED.value
            }
            response = client.post("/api/charge/start", json={"id_tag": "TEST"})
            assert response.status_code == 200

            # Şarj durdur
            response = client.post("/api/charge/stop", json={})
            assert response.status_code == 200

    def test_error_recovery_flow(self, client, mock_esp32_bridge):
        """Hata kurtarma akışı"""
        # 1. ESP32 bağlantısı kopmuş
        mock_esp32_bridge.is_connected = False
        response = client.get("/api/status")
        assert response.status_code == 503

        # 2. Bağlantı yeniden kuruldu
        mock_esp32_bridge.is_connected = True
        mock_esp32_bridge.get_status.return_value = {"STATE": 1}
        response = client.get("/api/status")
        assert response.status_code == 200

        # 3. Normal işlemler devam edebilir
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        assert response.status_code == 200

    def test_rapid_state_changes(self, client, mock_esp32_bridge):
        """Hızlı state değişiklikleri"""
        states = [1, 2, 3, 4, 5, 6, 7]

        for state in states:
            mock_esp32_bridge.get_status.return_value = {
                "STATE": state.value if hasattr(state, "value") else state
            }
            response = client.get("/api/status")
            assert response.status_code == 200
            assert response.json()["data"]["STATE"] == state


@pytest.mark.asyncio
async def test_ocpp_remote_ops_v201_local_csms_server():
    """
    OCPP Phase-1: station adapter Remote Start/Stop end-to-end (local CSMS).

    - Start a local websocket CSMS server (OCPP 2.0.1) with BasicAuth check
    - Run station adapter against it
    - Send RequestStartTransaction + RequestStopTransaction
    - Assert station emits TransactionEvent(Started/Ended)
    """
    import websockets

    from ocpp.routing import on
    from ocpp.v201 import ChargePoint, call, call_result, datatypes, enums

    # Import station adapter from /ocpp folder (not a package)
    sys.path.insert(0, str(Path(__file__).parent.parent / "ocpp"))
    from handlers import Ocpp201Adapter  # type: ignore

    @dataclass
    class _Cfg:
        station_name: str
        station_password: str
        ocpp201_url: str
        ocpp16_url: str = "ws://127.0.0.1/unused"
        primary: str = "201"
        poc_mode: bool = False
        once_mode: bool = False
        vendor_name: str = "ORGE"
        model: str = "AC-1"
        id_token: str = "TEST001"
        heartbeat_override_seconds: int = 10
        local_api_base_url: str = "http://localhost:8000"
        local_poll_enabled: bool = False
        local_poll_interval_seconds: int = 10
        poc_stop_source: str = "auto"
        poc_remote_stop_wait_seconds: int = 0
        poc_transaction_id: str = ""
        poc_remote_start_enabled: bool = False
        poc_remote_start_wait_seconds: int = 120
        poc_runbook_enabled: bool = False
        poc_runbook_wait_profile_seconds: int = 120
        poc_runbook_wait_stop_seconds: int = 120

    def _utc_now() -> str:
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    boot_seen = asyncio.Event()
    started_seen = asyncio.Event()
    ended_seen = asyncio.Event()

    started_payload: dict[str, Any] = {}
    ended_payload: dict[str, Any] = {}

    tx_id_holder: dict[str, str] = {}

    class CentralSystemCP(ChargePoint):
        @on("BootNotification")
        async def on_boot_notification(self, charging_station, reason, **kwargs):
            boot_seen.set()
            return call_result.BootNotification(
                status=enums.RegistrationStatusEnumType.accepted,
                current_time=_utc_now(),
                interval=30,
            )

        @on("StatusNotification")
        async def on_status_notification(self, **kwargs):
            return call_result.StatusNotification()

        @on("Heartbeat")
        async def on_heartbeat(self, **kwargs):
            return call_result.Heartbeat(current_time=_utc_now())

        @on("MeterValues")
        async def on_meter_values(self, **kwargs):
            return call_result.MeterValues()

        @on("TransactionEvent")
        async def on_transaction_event(self, **kwargs):
            # We only assert event_type and trigger_reason in this Phase-1 test.
            event_type = kwargs.get("event_type")
            trigger_reason = kwargs.get("trigger_reason")
            tx_info = kwargs.get("transaction_info")
            transaction_id = (
                getattr(tx_info, "transaction_id", None) if tx_info else None
            )

            if (
                event_type == enums.TransactionEventEnumType.started
                and trigger_reason == enums.TriggerReasonEnumType.remote_start
            ):
                started_payload.update(
                    {
                        "event_type": str(event_type),
                        "trigger_reason": str(trigger_reason),
                        "transaction_id": str(transaction_id),
                    }
                )
                started_seen.set()

            if (
                event_type == enums.TransactionEventEnumType.ended
                and trigger_reason == enums.TriggerReasonEnumType.remote_stop
            ):
                ended_payload.update(
                    {
                        "event_type": str(event_type),
                        "trigger_reason": str(trigger_reason),
                        "transaction_id": str(transaction_id),
                    }
                )
                ended_seen.set()

            return call_result.TransactionEvent()

    def _get_auth_header(ws: Any) -> str | None:
        # websockets 15 uses ServerConnection with `.request.headers`
        req = getattr(ws, "request", None)
        if req is not None:
            headers = getattr(req, "headers", None)
            if headers is not None:
                return headers.get("Authorization")
        # older API compatibility
        headers = getattr(ws, "request_headers", None)
        if headers is not None:
            return headers.get("Authorization")
        return None

    async def _ws_handler(ws):
        # Verify BasicAuth header (secret-free check)
        auth = _get_auth_header(ws)
        assert auth and auth.startswith("Basic ")
        raw = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
        assert raw == "ORGE_AC_001:testpw"

        cp = CentralSystemCP("ORGE_AC_001", ws)
        runner = asyncio.create_task(cp.start())
        try:
            await asyncio.wait_for(boot_seen.wait(), timeout=10)

            # Remote Start
            id_token = datatypes.IdTokenType(
                id_token="TEST001", type=enums.IdTokenEnumType.central
            )
            res = await cp.call(
                call.RequestStartTransaction(
                    id_token=id_token, remote_start_id=1781880852, evse_id=1
                ),
                suppress=False,
            )
            assert (
                res.status == enums.RequestStartStopStatusEnumType.accepted
            ), f"unexpected start status: {res}"
            assert getattr(res, "transaction_id", None)
            tx_id_holder["tx_id"] = str(res.transaction_id)

            await asyncio.wait_for(started_seen.wait(), timeout=10)

            # Remote Stop
            res2 = await cp.call(
                call.RequestStopTransaction(transaction_id=tx_id_holder["tx_id"]),
                suppress=False,
            )
            assert (
                res2.status == enums.RequestStartStopStatusEnumType.accepted
            ), f"unexpected stop status: {res2}"

            await asyncio.wait_for(ended_seen.wait(), timeout=10)
        finally:
            runner.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await runner

    server = await websockets.serve(
        _ws_handler, "127.0.0.1", 0, subprotocols=["ocpp2.0.1"]
    )
    port = server.sockets[0].getsockname()[1]

    cfg = _Cfg(
        station_name="ORGE_AC_001",
        station_password="testpw",
        ocpp201_url=f"ws://127.0.0.1:{port}/ocpp/ORGE_AC_001",
    )
    adapter = Ocpp201Adapter(cfg)
    adapter_task = asyncio.create_task(adapter.run())
    try:
        await asyncio.wait_for(ended_seen.wait(), timeout=20)
        assert started_payload.get("transaction_id"), started_payload
        assert ended_payload.get("transaction_id"), ended_payload
        assert ended_payload["transaction_id"] == started_payload["transaction_id"]
    finally:
        adapter_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await adapter_task
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_ocpp_v16_adapter_boot_status_heartbeat_local_csms_server():
    """
    OCPP 1.6J (v16) fallback adapter smoke (local CSMS).

    - Start a local websocket CSMS server (OCPP 1.6) with BasicAuth check
    - Run station v16 adapter (once_mode=True)
    - Assert station sends BootNotification + StatusNotification + Heartbeat
    """
    import websockets

    from ocpp.routing import on
    from ocpp.v16 import ChargePoint, call_result

    # Import station adapter from /ocpp folder (not a package)
    sys.path.insert(0, str(Path(__file__).parent.parent / "ocpp"))
    from main import Ocpp16Adapter  # type: ignore

    @dataclass
    class _Cfg:
        station_name: str
        station_password: str
        ocpp16_url: str
        ocpp201_url: str = "ws://127.0.0.1/unused"
        primary: str = "16"
        poc_mode: bool = False
        once_mode: bool = True
        vendor_name: str = "ORGE"
        model: str = "AC-1"
        id_token: str = "TEST001"
        heartbeat_override_seconds: int = 0
        local_api_base_url: str = "http://localhost:8000"
        local_poll_enabled: bool = False
        local_poll_interval_seconds: int = 10
        poc_stop_source: str = "auto"
        poc_remote_stop_wait_seconds: int = 0
        poc_transaction_id: str = ""
        poc_remote_start_enabled: bool = False
        poc_remote_start_wait_seconds: int = 120
        poc_runbook_enabled: bool = False
        poc_runbook_wait_profile_seconds: int = 120
        poc_runbook_wait_stop_seconds: int = 120

    def _utc_now() -> str:
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    boot_seen = asyncio.Event()
    status_seen = asyncio.Event()
    hb_seen = asyncio.Event()

    class CentralSystemCP(ChargePoint):
        @on("BootNotification")
        async def on_boot_notification(self, **kwargs):
            boot_seen.set()
            return call_result.BootNotification(
                current_time=_utc_now(), interval=30, status="Accepted"
            )

        @on("StatusNotification")
        async def on_status_notification(self, **kwargs):
            status_seen.set()
            return call_result.StatusNotification()

        @on("Heartbeat")
        async def on_heartbeat(self, **kwargs):
            hb_seen.set()
            return call_result.Heartbeat(current_time=_utc_now())

    def _get_auth_header(ws: Any) -> str | None:
        req = getattr(ws, "request", None)
        if req is not None:
            headers = getattr(req, "headers", None)
            if headers is not None:
                return headers.get("Authorization")
        headers = getattr(ws, "request_headers", None)
        if headers is not None:
            return headers.get("Authorization")
        return None

    async def _ws_handler(ws):
        # Verify BasicAuth header (secret-free check)
        auth = _get_auth_header(ws)
        assert auth and auth.startswith("Basic ")
        raw = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
        assert raw == "ORGE_AC_001:testpw"

        cp = CentralSystemCP("ORGE_AC_001", ws)
        runner = asyncio.create_task(cp.start())
        try:
            await asyncio.wait_for(boot_seen.wait(), timeout=10)
            await asyncio.wait_for(status_seen.wait(), timeout=10)
            await asyncio.wait_for(hb_seen.wait(), timeout=10)
        finally:
            runner.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await runner

    server = await websockets.serve(
        _ws_handler, "127.0.0.1", 0, subprotocols=["ocpp1.6"]
    )
    port = server.sockets[0].getsockname()[1]

    cfg = _Cfg(
        station_name="ORGE_AC_001",
        station_password="testpw",
        ocpp16_url=f"ws://127.0.0.1:{port}/ocpp16/ORGE_AC_001",
    )
    adapter = Ocpp16Adapter(cfg)
    adapter_task = asyncio.create_task(adapter.run())
    try:
        await asyncio.wait_for(hb_seen.wait(), timeout=20)
        assert boot_seen.is_set()
        assert status_seen.is_set()
        assert hb_seen.is_set()
    finally:
        adapter_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await adapter_task
        server.close()
        await server.wait_closed()
