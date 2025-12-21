"""
OCPP 2.0.1 (v201) StationCP for --once JSON Evidence (Phase-1)

Created: 2025-12-21 20:18
Last Modified: 2025-12-21 20:18
Version: 0.1.0
Description:
  Factory for the ChargePoint subclass used by `--once` evidence runs.
  Captures inbound CALLs and their responses for secret-free diagnostics.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Type

from ocpp.routing import on


def make_once_v201_station_cp(
    *,
    ChargePoint: Any,
    cfg: Any,
    inbound: list[dict[str, Any]],
    utc_now_iso: Callable[[], str],
    dt: Any,
    call_result: Any,
    enums: Any,
) -> Type[Any]:
    """
    Return a ChargePoint subclass that:
      - Records inbound CALLs (unique_id + action)
      - Records CallResult/CallError responses to those CALLs
      - Exposes asyncio.Events for runbook flows (remote start/stop, profile)
    """

    class StationCP(ChargePoint):
        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            self._inbound_by_uid: dict[str, dict[str, Any]] = {}

            # Phase-1.3: remote stop mapping signal
            self._remote_stop_event = asyncio.Event()
            self._remote_stop_transaction_id: str | None = None
            self._remote_stop_seen_utc: str | None = None

            # Phase-1.4: remote start mapping signal
            self._remote_start_event = asyncio.Event()
            self._remote_start_seen_utc: str | None = None
            self._remote_start_id_token: dt.IdTokenType | None = None
            self._remote_start_id: int | None = None
            self._remote_start_evse_id: int | None = None

            # Phase-1.4(B): SetChargingProfile evidence
            self._set_charging_profile_event = asyncio.Event()
            self._last_profile_summary: dict[str, Any] | None = None

        async def route_message(self, raw_msg: str):
            # Best-effort: capture inbound CALL action + unique_id for evidence.
            try:
                msg = json.loads(raw_msg)
                if (
                    isinstance(msg, list)
                    and len(msg) >= 4
                    and int(msg[0]) == 2
                    and isinstance(msg[1], str)
                    and isinstance(msg[2], str)
                ):
                    uid = msg[1]
                    action = msg[2]
                    entry = {
                        "direction": "inbound",
                        "utc": utc_now_iso(),
                        "unique_id": uid,
                        "action": action,
                        "response_type": None,
                        "callerror": None,
                    }
                    inbound.append(entry)
                    self._inbound_by_uid[uid] = entry
            except Exception:
                pass
            return await super().route_message(raw_msg)

        async def _send(self, message: str):
            # Capture responses to inbound CALLs (CALLRESULT / CALLERROR).
            try:
                msg = json.loads(message)
                if isinstance(msg, list) and len(msg) >= 3:
                    msg_type = int(msg[0])
                    uid = msg[1] if isinstance(msg[1], str) else None
                    if uid and uid in self._inbound_by_uid:
                        entry = self._inbound_by_uid[uid]
                        if msg_type == 3:
                            entry["response_type"] = "CallResult"
                            entry["callerror"] = False
                        elif msg_type == 4:
                            entry["response_type"] = "CallError"
                            entry["callerror"] = True
                            # [4, uniqueId, errorCode, errorDescription, errorDetails]
                            if len(msg) >= 5:
                                entry["error_code"] = msg[2]
                                entry["error_description"] = msg[3]
            except Exception:
                pass
            return await super()._send(message)

        @on("GetBaseReport")
        def on_get_base_report(self, request_id: int, report_base: str, **kwargs):
            return call_result.GetBaseReport(
                status=enums.GenericDeviceModelStatusEnumType.accepted
            )

        @on("GetReport")
        def on_get_report(self, **kwargs):
            # Minimal safe response (Phase-1): we don't generate report data here.
            return call_result.GetReport(
                status=enums.GenericDeviceModelStatusEnumType.not_supported
            )

        @on("GetLog")
        def on_get_log(self, **kwargs):
            # Minimal safe response (Phase-1): do not generate/download log files here.
            return call_result.GetLog(
                status=enums.LogStatusEnumType.rejected, filename=""
            )

        @on("GetVariables")
        def on_get_variables(self, get_variable_data: list, **kwargs):
            results: list[dt.GetVariableResultType] = []
            for item in get_variable_data:
                if hasattr(item, "component") and hasattr(item, "variable"):
                    component = item.component
                    variable = item.variable
                    attr_type = getattr(item, "attribute_type", None)
                else:
                    component = (
                        item.get("component") if isinstance(item, dict) else None
                    )
                    variable = item.get("variable") if isinstance(item, dict) else None
                    attr_type = (
                        item.get("attribute_type") if isinstance(item, dict) else None
                    )
                results.append(
                    dt.GetVariableResultType(
                        attribute_status=enums.GetVariableStatusEnumType.unknown_component,
                        component=component,
                        variable=variable,
                        attribute_type=attr_type,
                    )
                )
            return call_result.GetVariables(get_variable_result=results)

        @on("SetVariables")
        def on_set_variables(self, set_variable_data: list, **kwargs):
            results: list[dt.SetVariableResultType] = []
            for item in set_variable_data:
                if hasattr(item, "component") and hasattr(item, "variable"):
                    component = item.component
                    variable = item.variable
                    attr_type = getattr(item, "attribute_type", None)
                else:
                    component = (
                        item.get("component") if isinstance(item, dict) else None
                    )
                    variable = item.get("variable") if isinstance(item, dict) else None
                    attr_type = (
                        item.get("attribute_type") if isinstance(item, dict) else None
                    )
                results.append(
                    dt.SetVariableResultType(
                        attribute_status=enums.SetVariableStatusEnumType.rejected,
                        component=component,
                        variable=variable,
                        attribute_type=attr_type,
                    )
                )
            return call_result.SetVariables(set_variable_result=results)

        @on("RequestStopTransaction")
        def on_request_stop_transaction(self, transaction_id: str, **kwargs):
            # Phase-1.3 mapping: this inbound call is treated as Remote stop source.
            self._remote_stop_transaction_id = transaction_id
            self._remote_stop_seen_utc = utc_now_iso()
            self._remote_stop_event.set()
            return call_result.RequestStopTransaction(
                status=enums.RequestStartStopStatusEnumType.accepted
            )

        @on("RequestStartTransaction")
        def on_request_start_transaction(
            self,
            id_token: dt.IdTokenType,
            remote_start_id: int,
            evse_id: int | None = None,
            **kwargs,
        ):
            # Phase-1.4 mapping: this inbound call is treated as Remote start source.
            self._remote_start_seen_utc = utc_now_iso()
            self._remote_start_id_token = id_token
            self._remote_start_id = remote_start_id
            self._remote_start_evse_id = evse_id
            self._remote_start_event.set()

            # Return Accepted; provide transactionId if caller wants determinism.
            tx_id = None
            if getattr(cfg, "poc_transaction_id", ""):
                tx_id = cfg.poc_transaction_id
            return call_result.RequestStartTransaction(
                status=enums.RequestStartStopStatusEnumType.accepted,
                transaction_id=tx_id,
            )

        @on("SetChargingProfile")
        def on_set_charging_profile(
            self,
            charging_profile: dt.ChargingProfileType,
            evse_id: int | None = None,
            **kwargs,
        ):
            # Phase-1.4(B): accept and record a short summary for evidence.
            summary: dict[str, Any] = {"evse_id": evse_id}
            try:
                # dt.ChargingProfileType is dataclass-like in python-ocpp
                summary["stack_level"] = getattr(charging_profile, "stack_level", None)
                summary["charging_profile_purpose"] = getattr(
                    charging_profile, "charging_profile_purpose", None
                )
                summary["charging_profile_kind"] = getattr(
                    charging_profile, "charging_profile_kind", None
                )
                sched = getattr(charging_profile, "charging_schedule", None)
                if sched and isinstance(sched, list) and sched:
                    s0 = sched[0]
                    summary["rate_unit"] = getattr(s0, "charging_rate_unit", None)
                    periods = getattr(s0, "charging_schedule_period", None) or []
                    if periods:
                        p0 = periods[0]
                        summary["period_start"] = getattr(p0, "start_period", None)
                        summary["period_limit"] = getattr(p0, "limit", None)
            except Exception:
                pass
            self._last_profile_summary = summary
            self._set_charging_profile_event.set()
            return call_result.SetChargingProfile(
                status=enums.ChargingProfileStatusEnumType.accepted
            )

    return StationCP
