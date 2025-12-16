"""
OCPP Station Adapters (Phase-1)

Created: 2025-12-16 01:20
Last Modified: 2025-12-16 05:35
Version: 0.3.0
Description:
  Implements the Phase-1 approach:
  - Single transport behavior per adapter (websocket connect/reconnect, auth header, subprotocol)
  - Separate protocol adapters:
      * OCPP 2.0.1 (v201) adapter (primary)
      * OCPP 1.6J (v16) adapter (fallback)

NOTE:
  This module must remain isolated from the existing FastAPI/ESP32 runtime.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import ssl
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import websockets
from states import StationIdentity

from ocpp.routing import on


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _basic_auth_header(station_name: str, password: str) -> str:
    raw = f"{station_name}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _ssl_if_needed(url: str) -> Optional[ssl.SSLContext]:
    return ssl.create_default_context() if url.lower().startswith("wss://") else None


def _is_retryable_ws_error(exc: BaseException) -> bool:
    """
    Decide whether a connection error is retryable.

    Phase-1: be conservative; retry on most websocket/network errors.
    """
    return isinstance(exc, Exception)


async def _sleep_backoff(attempt: int) -> None:
    # Exponential backoff: 1s, 2s, 4s, ... (cap at 30s)
    delay = min(30.0, float(2 ** max(0, attempt)))
    await asyncio.sleep(delay)


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _http_get_json_sync(url: str, *, timeout_seconds: float) -> Optional[dict]:
    """
    Blocking HTTP GET that returns parsed JSON (dict) or None.

    Used via asyncio.to_thread to avoid blocking the event loop.
    """
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read()
        return json.loads(body.decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None
    except Exception:
        return None


async def _http_get_json(url: str, *, timeout_seconds: float = 2.0) -> Optional[dict]:
    return await asyncio.to_thread(
        _http_get_json_sync, url, timeout_seconds=timeout_seconds
    )


class Ocpp201Adapter:
    """OCPP 2.0.1 (v201) station adapter."""

    def __init__(self, cfg: Any):
        # cfg is OcppRuntimeConfig from ocpp/main.py; kept as Any to avoid package import issues.
        self.cfg = cfg
        self.identity = StationIdentity(
            station_name=cfg.station_name,
            vendor_name=cfg.vendor_name,
            model=cfg.model,
            firmware_version="ocpp-phase1",
        )

    async def run(self) -> None:
        from ocpp.v201 import ChargePoint, call, call_result, datatypes, enums

        class StationCP(ChargePoint):
            # CSMS may send inventory/model queries; accept them in Phase-1 to avoid breaking the flow.
            @on("GetBaseReport")
            def on_get_base_report(self, request_id: int, report_base: str, **kwargs):
                return call_result.GetBaseReport(
                    status=enums.GenericDeviceModelStatusEnumType.accepted
                )

            @on("GetReport")
            def on_get_report(self, request_id: int, **kwargs):
                return call_result.GetReport(
                    status=enums.GenericDeviceModelStatusEnumType.accepted
                )

            @on("GetLog")
            def on_get_log(self, request_id: int, **kwargs):
                return call_result.GetLog(status=enums.LogStatusEnumType.rejected)

            @on("GetVariables")
            def on_get_variables(self, get_variable_data, **kwargs):
                results = []

                def _component(obj):
                    if isinstance(obj, datatypes.ComponentType):
                        return obj
                    if isinstance(obj, dict):
                        evse = obj.get("evse")
                        evse_obj = None
                        if isinstance(evse, dict):
                            evse_obj = datatypes.EVSEType(
                                id=evse.get("id"),
                                connector_id=evse.get("connector_id"),
                            )
                        return datatypes.ComponentType(
                            name=obj.get("name"),
                            instance=obj.get("instance"),
                            evse=evse_obj,
                        )
                    return datatypes.ComponentType(name="Unknown")

                def _variable(obj):
                    if isinstance(obj, datatypes.VariableType):
                        return obj
                    if isinstance(obj, dict):
                        return datatypes.VariableType(
                            name=obj.get("name"), instance=obj.get("instance")
                        )
                    return datatypes.VariableType(name="Unknown")

                for item in get_variable_data:
                    if isinstance(item, dict):
                        comp = _component(item.get("component"))
                        var = _variable(item.get("variable"))
                        attr_type = item.get("attribute_type")
                    else:
                        comp = _component(getattr(item, "component", None))
                        var = _variable(getattr(item, "variable", None))
                        attr_type = getattr(item, "attribute_type", None)

                    results.append(
                        datatypes.GetVariableResultType(
                            attribute_status=enums.GetVariableStatusEnumType.unknown_variable,
                            component=comp,
                            variable=var,
                            attribute_type=attr_type,
                        )
                    )

                return call_result.GetVariables(get_variable_result=results)

        url = self.cfg.ocpp201_url
        headers = {
            "Authorization": _basic_auth_header(
                self.cfg.station_name, self.cfg.station_password
            )
        }

        attempt = 0
        while True:
            try:
                async with websockets.connect(
                    url,
                    subprotocols=["ocpp2.0.1"],
                    additional_headers=headers,
                    ssl=_ssl_if_needed(url),
                    open_timeout=10,
                ) as ws:
                    cp = StationCP(self.cfg.station_name, ws)
                    runner = asyncio.create_task(cp.start())
                    try:
                        if self.cfg.poc_mode:
                            await self._run_poc(
                                cp, call=call, datatypes=datatypes, enums=enums
                            )
                            return

                        if self.cfg.once_mode:
                            await self._run_once(
                                cp, call=call, datatypes=datatypes, enums=enums
                            )
                            return

                        await self._run_daemon(
                            cp, call=call, datatypes=datatypes, enums=enums
                        )
                    finally:
                        runner.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await runner

                # Normal websocket close: reset attempt and reconnect.
                attempt = 0
                await _sleep_backoff(attempt=0)
            except BaseException as e:
                if not _is_retryable_ws_error(e):
                    raise
                attempt += 1
                print(f"[OCPP] v201 reconnect attempt={attempt} error={e}")
                await _sleep_backoff(attempt=attempt)

    async def _run_poc(self, cp: Any, *, call: Any, datatypes: Any, enums: Any) -> None:
        """
        Phase-1 PoC message sequence:
        BootNotification → Authorize(TEST001) → StatusNotification →
        TransactionEvent(started/ended) → MeterValues(Energy.Active.Import.Register)
        """

        def _energy_mv(kwh: float) -> Any:
            return datatypes.MeterValueType(
                timestamp=_utc_now_iso(),
                sampled_value=[
                    datatypes.SampledValueType(
                        value=kwh,
                        measurand=enums.MeasurandEnumType.energy_active_import_register,
                        unit_of_measure=datatypes.UnitOfMeasureType(
                            unit=enums.StandardizedUnitsOfMeasureType.kwh
                        ),
                    )
                ],
            )

        async def _call(label: str, payload: Any) -> Any:
            unique_id = str(uuid.uuid4())
            ts = _utc_now_iso()
            res = await cp.call(payload, suppress=False, unique_id=unique_id)
            print(f"[OCPP/PoC] {label} utc={ts} unique_id={unique_id} result={res}")
            return res

        await _call(
            "BootNotification",
            call.BootNotification(
                charging_station=datatypes.ChargingStationType(
                    vendor_name=self.identity.vendor_name,
                    model=self.identity.model,
                    serial_number=self.identity.station_name,
                    firmware_version=self.identity.firmware_version,
                ),
                reason=enums.BootReasonEnumType.power_up,
            ),
        )

        id_token = datatypes.IdTokenType(
            id_token=self.cfg.id_token,
            type=enums.IdTokenEnumType.central,
        )
        auth_res = await _call("Authorize", call.Authorize(id_token=id_token))
        print(
            f"[OCPP/PoC] Authorize is SoT, response.id_token_info={getattr(auth_res, 'id_token_info', None)}"
        )

        await _call(
            "StatusNotification(Available)",
            call.StatusNotification(
                timestamp=_utc_now_iso(),
                connector_status=enums.ConnectorStatusEnumType.available,
                evse_id=1,
                connector_id=1,
            ),
        )

        tx_id = str(uuid.uuid4())
        evse = datatypes.EVSEType(id=1, connector_id=1)

        started_res = await _call(
            "TransactionEvent(Started)",
            call.TransactionEvent(
                event_type=enums.TransactionEventEnumType.started,
                timestamp=_utc_now_iso(),
                trigger_reason=enums.TriggerReasonEnumType.authorized,
                seq_no=1,
                transaction_info=datatypes.TransactionType(transaction_id=tx_id),
                evse=evse,
                id_token=id_token,
                meter_value=[_energy_mv(1000.00)],
            ),
        )
        print(
            "[OCPP/PoC] TransactionEvent response id_token_info expected None, got:",
            getattr(started_res, "id_token_info", None),
        )

        await _call(
            "MeterValues(Energy.Active.Import.Register)",
            call.MeterValues(
                evse_id=1,
                meter_value=[_energy_mv(1000.10)],
            ),
        )

        ended_res = await _call(
            "TransactionEvent(Ended)",
            call.TransactionEvent(
                event_type=enums.TransactionEventEnumType.ended,
                timestamp=_utc_now_iso(),
                trigger_reason=enums.TriggerReasonEnumType.ev_departed,
                seq_no=2,
                transaction_info=datatypes.TransactionType(
                    transaction_id=tx_id,
                    stopped_reason=enums.ReasonEnumType.ev_disconnected,
                ),
                evse=evse,
                id_token=id_token,
                meter_value=[_energy_mv(1000.20)],
            ),
        )
        print(
            "[OCPP/PoC] TransactionEvent(Ended) response id_token_info expected None, got:",
            getattr(ended_res, "id_token_info", None),
        )

    async def _run_once(
        self, cp: Any, *, call: Any, datatypes: Any, enums: Any
    ) -> None:
        """
        Non-daemon smoke test:
        - Send BootNotification
        - Send StatusNotification(Available)
        - Send one Heartbeat
        Then exit.
        """
        interval = await self._send_boot(
            cp, call=call, datatypes=datatypes, enums=enums
        )
        await self._send_initial_status(cp, call=call, enums=enums)
        await self._send_heartbeat(cp, call=call)
        print(f"[OCPP] v201 once-mode complete (boot_interval={interval})")

    async def _run_daemon(
        self, cp: Any, *, call: Any, datatypes: Any, enums: Any
    ) -> None:
        """
        Daemon mode:
        - BootNotification (gets interval)
        - Initial StatusNotification(Available)
        - Periodic Heartbeat based on interval (or override)
        - Keep connection open
        """
        interval = await self._send_boot(
            cp, call=call, datatypes=datatypes, enums=enums
        )
        await self._send_initial_status(cp, call=call, enums=enums)

        hb_interval = int(getattr(self.cfg, "heartbeat_override_seconds", 0) or 0)
        if hb_interval <= 0:
            hb_interval = int(getattr(interval, "interval", interval) or 300)
        hb_interval = max(10, hb_interval)
        print(f"[OCPP] v201 daemon heartbeat_interval={hb_interval}s")

        async def _heartbeat_loop() -> None:
            while True:
                await asyncio.sleep(hb_interval)
                await self._send_heartbeat(cp, call=call)

        async def _local_poll_loop() -> None:
            if not bool(getattr(self.cfg, "local_poll_enabled", True)):
                return

            base = str(
                getattr(self.cfg, "local_api_base_url", "http://localhost:8000")
            ).rstrip("/")
            poll_s = int(getattr(self.cfg, "local_poll_interval_seconds", 10) or 10)
            poll_s = max(5, poll_s)

            station_status_url = f"{base}/api/station/status"
            meter_reading_url = f"{base}/api/meter/reading"

            # We already send initial StatusNotification(Available) at daemon start.
            last_connector_status: Optional[Any] = (
                enums.ConnectorStatusEnumType.available
            )
            last_energy_kwh: Optional[float] = None

            print(f"[OCPP] local API polling enabled base={base} interval={poll_s}s")

            while True:
                try:
                    station_payload = await _http_get_json(
                        station_status_url, timeout_seconds=2.0
                    )
                    connector_status = (
                        self._derive_connector_status_from_station_payload(
                            station_payload, enums=enums
                        )
                    )
                    if (
                        connector_status is not None
                        and connector_status != last_connector_status
                    ):
                        await self._send_status_notification(
                            cp,
                            call=call,
                            enums=enums,
                            connector_status=connector_status,
                        )
                        last_connector_status = connector_status

                    meter_payload = await _http_get_json(
                        meter_reading_url, timeout_seconds=2.0
                    )
                    energy_kwh = self._extract_energy_import_kwh_from_meter_payload(
                        meter_payload
                    )
                    if energy_kwh is not None:
                        if (
                            last_energy_kwh is not None
                            and energy_kwh + 1e-6 < last_energy_kwh
                        ):
                            print(
                                f"[OCPP] meter energy non-monotonic: new={energy_kwh} < last={last_energy_kwh} (skipped)"
                            )
                        elif (
                            last_energy_kwh is None
                            or abs(energy_kwh - last_energy_kwh) >= 0.01
                        ):
                            await self._send_energy_meter_values(
                                cp,
                                call=call,
                                datatypes=datatypes,
                                enums=enums,
                                energy_import_kwh=energy_kwh,
                            )
                            last_energy_kwh = energy_kwh
                except Exception as e:
                    print(f"[OCPP] local poll error: {e}")

                await asyncio.sleep(poll_s)

        hb_task = asyncio.create_task(_heartbeat_loop())
        poll_task = asyncio.create_task(_local_poll_loop())
        done, pending = await asyncio.wait(
            {hb_task, poll_task}, return_when=asyncio.FIRST_EXCEPTION
        )
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc:
                raise exc

    async def _send_boot(
        self, cp: Any, *, call: Any, datatypes: Any, enums: Any
    ) -> Any:
        boot_res = await cp.call(
            call.BootNotification(
                charging_station=datatypes.ChargingStationType(
                    vendor_name=self.identity.vendor_name,
                    model=self.identity.model,
                    serial_number=self.identity.station_name,
                    firmware_version=self.identity.firmware_version,
                ),
                reason=enums.BootReasonEnumType.power_up,
            ),
            suppress=False,
            unique_id=str(uuid.uuid4()),
        )
        print(
            f"[OCPP] v201 BootNotification status={getattr(boot_res, 'status', None)} interval={getattr(boot_res, 'interval', None)}"
        )
        return boot_res

    async def _send_initial_status(self, cp: Any, *, call: Any, enums: Any) -> None:
        await cp.call(
            call.StatusNotification(
                timestamp=_utc_now_iso(),
                connector_status=enums.ConnectorStatusEnumType.available,
                evse_id=1,
                connector_id=1,
            ),
            suppress=False,
            unique_id=str(uuid.uuid4()),
        )
        print("[OCPP] v201 StatusNotification(Available) sent")

    async def _send_heartbeat(self, cp: Any, *, call: Any) -> None:
        # Heartbeat has no payload in v201
        await cp.call(call.Heartbeat(), suppress=False, unique_id=str(uuid.uuid4()))
        print(f"[OCPP] v201 Heartbeat sent utc={_utc_now_iso()}")

    def _derive_connector_status_from_station_payload(
        self, payload: Optional[dict], *, enums: Any
    ) -> Optional[Any]:
        """
        Map local `/api/station/status` JSON -> OCPP v201 ConnectorStatusEnumType.

        We prefer `data.status.state_name` if present; otherwise fall back to
        `data.status.availability`.
        """
        if not payload or not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        status = data.get("status")
        if not isinstance(status, dict):
            return None

        state_name = status.get("state_name")
        availability = status.get("availability")

        state_name_s = str(state_name).upper() if state_name is not None else ""
        availability_s = str(availability).lower() if availability is not None else ""

        if state_name_s in {"FAULT_HARD", "HARDFAULT_END"}:
            return enums.ConnectorStatusEnumType.faulted
        if state_name_s in {"CHARGING", "PAUSED"}:
            return enums.ConnectorStatusEnumType.occupied
        if state_name_s in {"READY", "EV_CONNECTED"}:
            return enums.ConnectorStatusEnumType.reserved
        if state_name_s in {"CABLE_DETECT"}:
            return enums.ConnectorStatusEnumType.occupied
        if state_name_s in {"IDLE"}:
            return enums.ConnectorStatusEnumType.available

        if availability_s == "fault":
            return enums.ConnectorStatusEnumType.faulted
        if availability_s == "busy":
            return enums.ConnectorStatusEnumType.occupied
        if availability_s == "reserved":
            return enums.ConnectorStatusEnumType.reserved
        if availability_s == "available":
            return enums.ConnectorStatusEnumType.available

        return enums.ConnectorStatusEnumType.unavailable

    def _extract_energy_import_kwh_from_meter_payload(
        self, payload: Optional[dict]
    ) -> Optional[float]:
        """
        Extract kWh (kümülatif import) from `/api/meter/reading`.

        Expected APIResponse schema:
          { success: bool, data: { totals: { energy_import_kwh: float, ... }, energy_kwh: float, ... } }
        """
        if not payload or not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None

        totals = data.get("totals")
        if isinstance(totals, dict):
            v = _safe_float(totals.get("energy_import_kwh"))
            if v is not None:
                return v
            v = _safe_float(totals.get("energy_kwh"))
            if v is not None:
                return v
            v = _safe_float(totals.get("energy_total_kwh"))
            if v is not None:
                return v

        return _safe_float(data.get("energy_kwh"))

    async def _send_status_notification(
        self,
        cp: Any,
        *,
        call: Any,
        enums: Any,
        connector_status: Any,
    ) -> None:
        await cp.call(
            call.StatusNotification(
                timestamp=_utc_now_iso(),
                connector_status=connector_status,
                evse_id=1,
                connector_id=1,
            ),
            suppress=False,
            unique_id=str(uuid.uuid4()),
        )
        print(f"[OCPP] v201 StatusNotification sent status={connector_status}")

    async def _send_energy_meter_values(
        self,
        cp: Any,
        *,
        call: Any,
        datatypes: Any,
        enums: Any,
        energy_import_kwh: float,
    ) -> None:
        meter_value = datatypes.MeterValueType(
            timestamp=_utc_now_iso(),
            sampled_value=[
                datatypes.SampledValueType(
                    value=float(energy_import_kwh),
                    measurand=enums.MeasurandEnumType.energy_active_import_register,
                    unit_of_measure=datatypes.UnitOfMeasureType(
                        unit=enums.StandardizedUnitsOfMeasureType.kwh
                    ),
                )
            ],
        )
        await cp.call(
            call.MeterValues(evse_id=1, meter_value=[meter_value]),
            suppress=False,
            unique_id=str(uuid.uuid4()),
        )
        print(f"[OCPP] v201 MeterValues energy_import_kwh={energy_import_kwh}")


class Ocpp16Adapter:
    """OCPP 1.6J (v16) station adapter (fallback). Phase-1 keeps it minimal."""

    def __init__(self, cfg: Any):
        self.cfg = cfg
        self.identity = StationIdentity(
            station_name=cfg.station_name,
            vendor_name=cfg.vendor_name,
            model=cfg.model,
            firmware_version="ocpp-phase1",
        )

    async def run(self) -> None:
        from ocpp.v16 import ChargePoint, call

        # NOTE: Implementation will be expanded after OCPP 2.0.1 is stable.
        # For Phase-1 we keep this adapter as a placeholder that can connect and stay alive.
        url = self.cfg.ocpp16_url
        headers = {
            "Authorization": _basic_auth_header(
                self.cfg.station_name, self.cfg.station_password
            )
        }

        async with websockets.connect(
            url,
            subprotocols=["ocpp1.6"],
            additional_headers=headers,
            ssl=_ssl_if_needed(url),
            open_timeout=10,
        ) as ws:
            cp = ChargePoint(self.cfg.station_name, ws)
            runner = asyncio.create_task(cp.start())
            try:
                if self.cfg.poc_mode:
                    print(
                        "[OCPP/PoC] OCPP 1.6J PoC not implemented yet (Phase-1 priority is 2.0.1)."
                    )
                    return
                if self.cfg.once_mode:
                    # Minimal 1.6J smoke-test: BootNotification + Heartbeat then exit.
                    boot = await cp.call(
                        call.BootNotification(
                            charge_point_model=self.identity.model,
                            charge_point_vendor=self.identity.vendor_name,
                        ),
                        suppress=False,
                        unique_id=str(uuid.uuid4()),
                    )
                    print(
                        f"[OCPP] v16 BootNotification status={boot.status} interval={boot.interval}"
                    )

                    hb = await cp.call(
                        call.Heartbeat(), suppress=False, unique_id=str(uuid.uuid4())
                    )
                    print(f"[OCPP] v16 Heartbeat current_time={hb.current_time}")
                    return

                # Daemon placeholder: keep connection alive, send heartbeat at fixed interval.
                while True:
                    await asyncio.sleep(300)
                    await cp.call(
                        call.Heartbeat(), suppress=False, unique_id=str(uuid.uuid4())
                    )
            finally:
                runner.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runner
