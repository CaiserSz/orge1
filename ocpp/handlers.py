"""
OCPP Station Adapters (Phase-1)

Created: 2025-12-16 01:20
Last Modified: 2025-12-21 01:51
Version: 0.4.3
Description:
  Implements the Phase-1 approach:
  - Single transport behavior per adapter (websocket connect/reconnect, auth header, subprotocol)
  - OCPP 2.0.1 (v201) adapter (primary)
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from typing import Any, Optional

import websockets
from states import (
    LocalApiPoller,
    LocalApiPollerConfig,
    StationIdentity,
    basic_auth_header,
    run_poc_v201,
    ssl_if_needed,
    utc_now_iso,
)

from ocpp.routing import on


def _utc_now_iso() -> str:
    # Backward compatible alias (kept to minimize diffs inside this file).
    return utc_now_iso()


def _basic_auth_header(station_name: str, password: str) -> str:
    # Backward compatible alias
    return basic_auth_header(station_name, password)


def _ssl_if_needed(url: str):
    # Backward compatible alias
    return ssl_if_needed(url)


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


#
# NOTE:
# HTTP/json parsing helpers moved to `ocpp/states.py` to keep this file within
# size standards. Local API polling is now implemented via `LocalApiPoller`.
#


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

        cfg = self.cfg

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

            @on("RequestStartTransaction")
            async def on_request_start_transaction(
                self,
                id_token: datatypes.IdTokenType,
                remote_start_id: int,
                evse_id: int | None = None,
                **kwargs,
            ):
                # Phase-1.4: accept UI Remote Start and emit a Started TransactionEvent.
                tx_id = str(getattr(cfg, "poc_transaction_id", "") or "").strip()
                if not tx_id:
                    tx_id = f"RS_{remote_start_id}"
                tx_id = tx_id[:36]

                evse = datatypes.EVSEType(id=int(evse_id or 1), connector_id=1)

                print(
                    "[OCPP] v201 RequestStartTransaction received "
                    f"remote_start_id={remote_start_id} evse_id={getattr(evse, 'id', None)} tx_id={tx_id}"
                )

                async def _emit_started() -> None:
                    try:
                        await self.call(
                            call.TransactionEvent(
                                event_type=enums.TransactionEventEnumType.started,
                                timestamp=_utc_now_iso(),
                                trigger_reason=enums.TriggerReasonEnumType.remote_start,
                                seq_no=1,
                                transaction_info=datatypes.TransactionType(
                                    transaction_id=tx_id
                                ),
                                evse=evse,
                                id_token=id_token,
                            ),
                            suppress=False,
                            unique_id=str(uuid.uuid4()),
                        )
                        print(
                            "[OCPP] v201 TransactionEvent(Started) remote_start "
                            f"tx_id={tx_id} utc={_utc_now_iso()}"
                        )
                    except Exception as exc:
                        print(
                            "[OCPP] v201 TransactionEvent(Started) remote_start failed "
                            f"tx_id={tx_id} error={exc}"
                        )

                asyncio.create_task(_emit_started())

                return call_result.RequestStartTransaction(
                    status=enums.RequestStartStopStatusEnumType.accepted,
                    transaction_id=tx_id,
                )

            @on("RequestStopTransaction")
            async def on_request_stop_transaction(self, transaction_id: str, **kwargs):
                # Phase-1.4 UI Remote Stop: accept the request and optionally emit Ended.
                print(
                    "[OCPP] v201 RequestStopTransaction received "
                    f"transaction_id={transaction_id} utc={_utc_now_iso()}"
                )

                async def _emit_ended() -> None:
                    try:
                        await self.call(
                            call.TransactionEvent(
                                event_type=enums.TransactionEventEnumType.ended,
                                timestamp=_utc_now_iso(),
                                trigger_reason=enums.TriggerReasonEnumType.remote_stop,
                                seq_no=2,
                                transaction_info=datatypes.TransactionType(
                                    transaction_id=transaction_id,
                                    stopped_reason=enums.ReasonEnumType.remote,
                                ),
                            ),
                            suppress=False,
                            unique_id=str(uuid.uuid4()),
                        )
                        print(
                            "[OCPP] v201 TransactionEvent(Ended) remote_stop "
                            f"tx_id={transaction_id} utc={_utc_now_iso()}"
                        )
                    except Exception as exc:
                        print(
                            "[OCPP] v201 TransactionEvent(Ended) remote_stop failed "
                            f"tx_id={transaction_id} error={exc}"
                        )

                asyncio.create_task(_emit_ended())

                return call_result.RequestStopTransaction(
                    status=enums.RequestStartStopStatusEnumType.accepted
                )

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
                    # Keepalive: helps prevent idle disconnects and improves "connected_ids" stability.
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as ws:
                    cp = StationCP(self.cfg.station_name, ws)
                    runner = asyncio.create_task(cp.start())
                    try:
                        if self.cfg.poc_mode:
                            await run_poc_v201(
                                cp,
                                identity=self.identity,
                                id_token=self.cfg.id_token,
                                call=call,
                                datatypes=datatypes,
                                enums=enums,
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
                code = getattr(e, "code", None)
                reason = getattr(e, "reason", None)
                extra = ""
                if code is not None or reason is not None:
                    extra = f" code={code!r} reason={reason!r}"
                print(
                    f"[OCPP] v201 reconnect attempt={attempt} "
                    f"error_type={type(e).__name__} error={e}{extra}"
                )
                await _sleep_backoff(attempt=attempt)

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

            poller = LocalApiPoller(
                LocalApiPollerConfig(base_url=base, poll_interval_seconds=poll_s)
            )

            async def _on_status_change(label: str) -> None:
                # label: available/occupied/reserved/faulted/unavailable
                connector_status = getattr(
                    enums.ConnectorStatusEnumType,
                    label,
                    enums.ConnectorStatusEnumType.unavailable,
                )
                await self._send_status_notification(
                    cp, call=call, enums=enums, connector_status=connector_status
                )

            async def _on_energy_update(energy_kwh: float) -> None:
                await self._send_energy_meter_values(
                    cp,
                    call=call,
                    datatypes=datatypes,
                    enums=enums,
                    energy_import_kwh=energy_kwh,
                )

            id_token = datatypes.IdTokenType(
                id_token=getattr(self.cfg, "id_token", "TEST001"),
                type=enums.IdTokenEnumType.central,
            )
            evse = datatypes.EVSEType(id=1, connector_id=1)

            async def _on_session_started(
                session_id: str, energy_kwh: Optional[float]
            ) -> None:
                # Token SoT: Authorize is the only source of truth.
                await cp.call(
                    call.Authorize(id_token=id_token),
                    suppress=False,
                    unique_id=str(uuid.uuid4()),
                )

                meter_values = None
                if energy_kwh is not None:
                    meter_values = [
                        datatypes.MeterValueType(
                            timestamp=_utc_now_iso(),
                            sampled_value=[
                                datatypes.SampledValueType(
                                    value=float(energy_kwh),
                                    measurand=enums.MeasurandEnumType.energy_active_import_register,
                                    unit_of_measure=datatypes.UnitOfMeasureType(
                                        unit=enums.StandardizedUnitsOfMeasureType.kwh
                                    ),
                                )
                            ],
                        )
                    ]

                await cp.call(
                    call.TransactionEvent(
                        event_type=enums.TransactionEventEnumType.started,
                        timestamp=_utc_now_iso(),
                        trigger_reason=enums.TriggerReasonEnumType.authorized,
                        seq_no=1,
                        transaction_info=datatypes.TransactionType(
                            transaction_id=session_id,
                        ),
                        meter_value=meter_values,
                        evse=evse,
                        id_token=id_token,
                    ),
                    suppress=False,
                    unique_id=str(uuid.uuid4()),
                )
                print(f"[OCPP] v201 TransactionEvent(Started) tx_id={session_id}")

            async def _on_session_ended(
                session_id: str,
                energy_kwh: Optional[float],
                session_status: Optional[str],
            ) -> None:
                stopped_reason = enums.ReasonEnumType.other
                if str(session_status).upper() == "COMPLETED":
                    stopped_reason = enums.ReasonEnumType.ev_disconnected
                elif str(session_status).upper() == "CANCELLED":
                    stopped_reason = enums.ReasonEnumType.remote

                meter_values = None
                if energy_kwh is not None:
                    meter_values = [
                        datatypes.MeterValueType(
                            timestamp=_utc_now_iso(),
                            sampled_value=[
                                datatypes.SampledValueType(
                                    value=float(energy_kwh),
                                    measurand=enums.MeasurandEnumType.energy_active_import_register,
                                    unit_of_measure=datatypes.UnitOfMeasureType(
                                        unit=enums.StandardizedUnitsOfMeasureType.kwh
                                    ),
                                )
                            ],
                        )
                    ]

                await cp.call(
                    call.TransactionEvent(
                        event_type=enums.TransactionEventEnumType.ended,
                        timestamp=_utc_now_iso(),
                        trigger_reason=enums.TriggerReasonEnumType.ev_departed,
                        seq_no=2,
                        transaction_info=datatypes.TransactionType(
                            transaction_id=session_id,
                            stopped_reason=stopped_reason,
                        ),
                        meter_value=meter_values,
                        evse=evse,
                        id_token=id_token,
                    ),
                    suppress=False,
                    unique_id=str(uuid.uuid4()),
                )
                print(
                    f"[OCPP] v201 TransactionEvent(Ended) tx_id={session_id} status={session_status}"
                )

            await poller.run(
                on_status_change=_on_status_change,
                on_energy_update=_on_energy_update,
                on_session_started=_on_session_started,
                on_session_ended=_on_session_ended,
            )

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
                    serial_number=self.identity.station_name[:25],
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


#
# NOTE:
# OCPP 1.6J adapter moved to `ocpp/main.py` to keep this module within size
# standards without creating new files/folders.
#
