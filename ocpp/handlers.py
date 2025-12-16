"""
OCPP Station Adapters (Phase-1)

Created: 2025-12-16 01:20
Last Modified: 2025-12-16 05:00
Version: 0.2.0
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
import ssl
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

        while True:
            await asyncio.sleep(hb_interval)
            await self._send_heartbeat(cp, call=call)

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
