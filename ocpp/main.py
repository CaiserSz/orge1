"""
OCPP Station Client Runner (Phase-1)

Created: 2025-12-16 01:20
Last Modified: 2025-12-21 17:00
Version: 0.5.5
Description:
  OCPP station client entrypoint for Raspberry Pi (Python runtime).
  - Primary: OCPP 2.0.1 (v201)
  - Fallback: OCPP 1.6J (v16)

IMPORTANT:
  - This process is intentionally isolated from the existing FastAPI/ESP32 runtime.
  - It must NOT open the ESP32 serial port or mutate the current running API.
  - It only connects outward to CSMS via WebSocket (ws/wss).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import signal
import subprocess
import sys
import uuid
from dataclasses import dataclass, fields, is_dataclass
from typing import Any

import websockets
from states import (StationIdentity, basic_auth_header,
                    serial_number_for_station_name, ssl_if_needed, utc_now_iso)


def _dataclass_field_names(obj: Any) -> list[str]:
    return sorted([f.name for f in fields(obj)]) if is_dataclass(obj) else []


def _response_summary(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    out: dict[str, Any] = {}
    for key in ("status", "interval", "current_time"):
        if hasattr(obj, key):
            val = getattr(obj, key, None)
            if val is not None:
                out[key] = val
    return out


def _git_commit_short() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or None
    except Exception:
        return None


def _dist_version(dist_name: str) -> str | None:
    try:
        import importlib.metadata as md

        return md.version(dist_name)
    except Exception:
        return None


def _verify_python_ocpp_package() -> None:
    """
    Verify that the python-ocpp library is importable and not shadowed by local paths.

    Why:
    - Repo contains `/home/basar/charger/ocpp/` folder.
    - python-ocpp library is imported as `ocpp` (e.g. `ocpp.v201`, `ocpp.v16`).
    - Some environments may accidentally shadow the library, causing runtime import errors.

    This function is secret-free and raises a RuntimeError with an actionable message.
    """
    import importlib

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    try:
        ocpp_pkg = importlib.import_module("ocpp")
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency: python-ocpp library is not importable. "
            "Ensure the venv is created and requirements are installed "
            "(`./env/bin/pip install -r requirements.txt`)."
        ) from exc

    pkg_file = getattr(ocpp_pkg, "__file__", None)
    if not pkg_file:
        raise RuntimeError(
            "Python package conflict: `import ocpp` resolved to a namespace package "
            "(no __file__). This can happen if local paths shadow the python-ocpp library. "
            "Fix: run the station via the venv and avoid adding the repo root ahead of "
            "site-packages on PYTHONPATH."
        )

    pkg_file_abs = os.path.abspath(str(pkg_file))
    if pkg_file_abs.startswith(repo_root + os.sep):
        raise RuntimeError(
            "Python package conflict: `import ocpp` resolved to the repo path "
            f"({pkg_file_abs}). Expected python-ocpp from site-packages. "
            "Fix: ensure python-ocpp is installed in the venv and do not create "
            "`ocpp/__init__.py` inside this repo."
        )

    for mod_name in ("ocpp.routing", "ocpp.v201", "ocpp.v16"):
        try:
            importlib.import_module(mod_name)
        except Exception as exc:
            raise RuntimeError(
                f"python-ocpp appears incomplete or shadowed: failed to import `{mod_name}`: {exc}"
            ) from exc


async def _run_once_json(cfg: Any) -> dict[str, Any]:
    # `--once` MUST output a single JSON object and MUST NOT include secrets.
    started_utc = utc_now_iso()
    messages: list[dict[str, Any]] = []
    inbound: list[dict[str, Any]] = []
    notes: list[str] = []
    callerror = False
    protocol_timeout = False

    subprotocol = "ocpp2.0.1" if cfg.primary == "201" else "ocpp1.6"
    url = cfg.ocpp201_url if cfg.primary == "201" else cfg.ocpp16_url
    headers = {
        "Authorization": basic_auth_header(cfg.station_name, cfg.station_password)
    }

    def _final_report(*, finished: str) -> dict[str, Any]:
        return {
            "station_name": cfg.station_name,
            "endpoint": url,
            "subprotocol": subprotocol,
            "run_started_utc": started_utc,
            "run_finished_utc": finished,
            "auth": {"username": cfg.station_name},
            "result": {
                "callerror": bool(callerror),
                "protocol_timeout": bool(protocol_timeout),
                "notes": notes,
                "config": {
                    # Secret-free runtime config summary (for ops correlation).
                    "primary": getattr(cfg, "primary", None),
                    "ocpp201_url": getattr(cfg, "ocpp201_url", None),
                    "ocpp16_url": getattr(cfg, "ocpp16_url", None),
                    "vendor_name": getattr(cfg, "vendor_name", None),
                    "model": getattr(cfg, "model", None),
                    "heartbeat_override_seconds": getattr(
                        cfg, "heartbeat_override_seconds", None
                    ),
                    "local_poll_enabled": getattr(cfg, "local_poll_enabled", None),
                    "local_api_base_url": getattr(cfg, "local_api_base_url", None),
                    "local_poll_interval_seconds": getattr(
                        cfg, "local_poll_interval_seconds", None
                    ),
                },
                "build": {
                    "station_build_commit": _git_commit_short(),
                    "ocpp_lib_version": _dist_version("ocpp"),
                    "websockets_version": getattr(websockets, "__version__", None),
                    "runtime_mode": "once",
                    "phase": (
                        "phase-1.4"
                        if bool(
                            getattr(cfg, "poc_remote_start_enabled", False)
                            or getattr(cfg, "poc_runbook_enabled", False)
                        )
                        else ("phase-1.3" if bool(cfg.poc_mode) else "phase-1.1")
                    ),
                },
                "inbound_calls": inbound,
            },
            "messages": messages,
        }

    async def _send(cp: Any, req: Any, action: str) -> None:
        uid = str(uuid.uuid4())
        ts = utc_now_iso()
        res = await cp.call(req, suppress=False, unique_id=uid)
        messages.append(
            {
                "action": action,
                "utc": ts,
                "unique_id": uid,
                "request_keys": _dataclass_field_names(req),
                "response_summary": _response_summary(res),
            }
        )

    async def _send_safe(cp: Any, req: Any, action: str) -> Any:
        """
        Send a CALL and always append a message entry.
        Returns response on success. Raises on error (after recording).
        """
        uid = str(uuid.uuid4())
        ts = utc_now_iso()
        try:
            res = await cp.call(req, suppress=False, unique_id=uid)
            messages.append(
                {
                    "action": action,
                    "utc": ts,
                    "unique_id": uid,
                    "request_keys": _dataclass_field_names(req),
                    "response_summary": _response_summary(res),
                }
            )
            return res
        except Exception as exc:
            messages.append(
                {
                    "action": action,
                    "utc": ts,
                    "unique_id": uid,
                    "request_keys": _dataclass_field_names(req),
                    "response_summary": {"error": str(exc)},
                }
            )
            raise

    try:
        async with websockets.connect(
            url,
            subprotocols=[subprotocol],
            additional_headers=headers,
            ssl=ssl_if_needed(url),
            open_timeout=10,
        ) as ws:
            if cfg.primary == "201":
                from ocpp.routing import on
                from ocpp.v201 import ChargePoint, call, call_result
                from ocpp.v201 import datatypes as dt
                from ocpp.v201 import enums

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
                    def on_get_base_report(
                        self, request_id: int, report_base: str, **kwargs
                    ):
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
                                    item.get("component")
                                    if isinstance(item, dict)
                                    else None
                                )
                                variable = (
                                    item.get("variable")
                                    if isinstance(item, dict)
                                    else None
                                )
                                attr_type = (
                                    item.get("attribute_type")
                                    if isinstance(item, dict)
                                    else None
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
                                    item.get("component")
                                    if isinstance(item, dict)
                                    else None
                                )
                                variable = (
                                    item.get("variable")
                                    if isinstance(item, dict)
                                    else None
                                )
                                attr_type = (
                                    item.get("attribute_type")
                                    if isinstance(item, dict)
                                    else None
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
                    def on_request_stop_transaction(
                        self, transaction_id: str, **kwargs
                    ):
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
                            summary["stack_level"] = getattr(
                                charging_profile, "stack_level", None
                            )
                            summary["charging_profile_purpose"] = getattr(
                                charging_profile, "charging_profile_purpose", None
                            )
                            summary["charging_profile_kind"] = getattr(
                                charging_profile, "charging_profile_kind", None
                            )
                            sched = getattr(charging_profile, "charging_schedule", None)
                            if sched and isinstance(sched, list) and sched:
                                s0 = sched[0]
                                summary["rate_unit"] = getattr(
                                    s0, "charging_rate_unit", None
                                )
                                periods = (
                                    getattr(s0, "charging_schedule_period", None) or []
                                )
                                if periods:
                                    p0 = periods[0]
                                    summary["period_start"] = getattr(
                                        p0, "start_period", None
                                    )
                                    summary["period_limit"] = getattr(p0, "limit", None)
                        except Exception:
                            pass
                        self._last_profile_summary = summary
                        self._set_charging_profile_event.set()
                        return call_result.SetChargingProfile(
                            status=enums.ChargingProfileStatusEnumType.accepted
                        )

                cp: Any = StationCP(cfg.station_name, ws)
                runner = asyncio.create_task(cp.start())
                try:
                    await _send(
                        cp,
                        call.BootNotification(
                            charging_station=dt.ChargingStationType(
                                vendor_name=cfg.vendor_name,
                                model=cfg.model,
                                serial_number=serial_number_for_station_name(
                                    cfg.station_name
                                ),
                                firmware_version="ocpp-phase1",
                            ),
                            reason=enums.BootReasonEnumType.power_up,
                        ),
                        "BootNotification",
                    )
                    await _send(
                        cp,
                        call.StatusNotification(
                            timestamp=utc_now_iso(),
                            connector_status=enums.ConnectorStatusEnumType.available,
                            evse_id=1,
                            connector_id=1,
                        ),
                        "StatusNotification",
                    )
                    # Phase-1.x minimum evidence: always emit at least one Heartbeat early.
                    await _send(cp, call.Heartbeat(), "Heartbeat")
                    # Phase-1.x PoC evidence (enabled via --poc + --once).
                    if cfg.poc_mode:
                        # Phase-1.4 (A/B/C) Runbook:
                        # A) Wait for inbound RequestStartTransaction → send TransactionEvent(Started) (RemoteStart)
                        # B) Wait for inbound SetChargingProfile → record summary
                        # C) Wait for inbound RequestStopTransaction → send TransactionEvent(Ended) (Remote/RemoteStop)
                        if bool(getattr(cfg, "poc_runbook_enabled", False)):
                            start_wait_s = int(
                                getattr(cfg, "poc_remote_start_wait_seconds", 120)
                            )
                            profile_wait_s = int(
                                getattr(cfg, "poc_runbook_wait_profile_seconds", 120)
                            )
                            stop_wait_s = int(
                                getattr(cfg, "poc_runbook_wait_stop_seconds", 120)
                            )
                            notes.append(
                                "phase14: runbook enabled "
                                f"start_wait_s={start_wait_s} profile_wait_s={profile_wait_s} stop_wait_s={stop_wait_s}"
                            )

                            # A) Wait for RequestStartTransaction inbound
                            try:
                                await asyncio.wait_for(
                                    cp._remote_start_event.wait(),
                                    timeout=start_wait_s,
                                )
                            except asyncio.TimeoutError:
                                callerror = True
                                protocol_timeout = True
                                notes.append(
                                    "phase14: timeout waiting for RequestStartTransaction"
                                )
                                raise

                            remote_start_id = cp._remote_start_id
                            remote_start_seen_utc = cp._remote_start_seen_utc
                            remote_start_evse_id = cp._remote_start_evse_id or 1
                            remote_start_id_token = cp._remote_start_id_token

                            tx_id = (cfg.poc_transaction_id or "").strip()
                            if not tx_id:
                                tx_id = (
                                    f"RS_{remote_start_id}"
                                    if remote_start_id
                                    else uuid.uuid4().hex
                                )
                            tx_id = tx_id[:36]

                            started_ts = utc_now_iso()
                            started_req = call.TransactionEvent(
                                event_type=enums.TransactionEventEnumType.started,
                                timestamp=started_ts,
                                trigger_reason=enums.TriggerReasonEnumType.remote_start,
                                seq_no=1,
                                transaction_info=dt.TransactionType(
                                    transaction_id=tx_id
                                ),
                                evse=dt.EVSEType(
                                    id=int(remote_start_evse_id), connector_id=1
                                ),
                                id_token=remote_start_id_token,
                            )
                            await _send_safe(
                                cp, started_req, "TransactionEvent(Started)"
                            )
                            notes.append(
                                "phase14: started_trigger_reason=RemoteStart "
                                f"tx_id={tx_id} remote_start_id={remote_start_id} "
                                f"seen_utc={remote_start_seen_utc}"
                            )

                            # B) Wait for SetChargingProfile inbound (required for runbook)
                            try:
                                await asyncio.wait_for(
                                    cp._set_charging_profile_event.wait(),
                                    timeout=profile_wait_s,
                                )
                            except asyncio.TimeoutError:
                                callerror = True
                                protocol_timeout = True
                                notes.append(
                                    "phase14: timeout waiting for SetChargingProfile"
                                )
                                raise

                            if cp._last_profile_summary is not None:
                                notes.append(
                                    "phase14: set_charging_profile_summary="
                                    + json.dumps(
                                        cp._last_profile_summary,
                                        ensure_ascii=False,
                                        sort_keys=True,
                                    )
                                )

                            # C) Wait for RequestStopTransaction inbound (required for runbook)
                            try:
                                await asyncio.wait_for(
                                    cp._remote_stop_event.wait(),
                                    timeout=stop_wait_s,
                                )
                            except asyncio.TimeoutError:
                                callerror = True
                                protocol_timeout = True
                                notes.append(
                                    "phase14: timeout waiting for RequestStopTransaction"
                                )
                                raise

                            remote_stop_seen_utc = cp._remote_stop_seen_utc
                            remote_stop_tx_id = cp._remote_stop_transaction_id
                            notes.append(
                                "phase14: stop_source=remote inbound=RequestStopTransaction "
                                f"inbound_tx_id={remote_stop_tx_id} seen_utc={remote_stop_seen_utc}"
                            )

                            ended_ts = utc_now_iso()
                            ended_req = call.TransactionEvent(
                                event_type=enums.TransactionEventEnumType.ended,
                                timestamp=ended_ts,
                                trigger_reason=enums.TriggerReasonEnumType.remote_stop,
                                seq_no=2,
                                transaction_info=dt.TransactionType(
                                    transaction_id=tx_id,
                                    stopped_reason=enums.ReasonEnumType.remote,
                                ),
                                evse=dt.EVSEType(
                                    id=int(remote_start_evse_id), connector_id=1
                                ),
                                id_token=remote_start_id_token,
                            )
                            await _send_safe(cp, ended_req, "TransactionEvent(Ended)")
                            notes.append(
                                "phase14: ended_stopped_reason=Remote "
                                "trigger_reason=RemoteStop seq_no_end=2"
                            )

                            await _send(cp, call.Heartbeat(), "Heartbeat")
                            return _final_report(finished=utc_now_iso())

                        # Phase-1.4 (A) Remote Start only evidence: wait for inbound RequestStartTransaction.
                        if bool(getattr(cfg, "poc_remote_start_enabled", False)):
                            wait_s = int(
                                getattr(cfg, "poc_remote_start_wait_seconds", 120)
                            )
                            notes.append(
                                f"phase14: waiting_for=RequestStartTransaction timeout_seconds={wait_s}"
                            )
                            try:
                                await asyncio.wait_for(
                                    cp._remote_start_event.wait(), timeout=wait_s
                                )
                            except asyncio.TimeoutError:
                                callerror = True
                                notes.append(
                                    "phase14: timeout waiting for RequestStartTransaction"
                                )
                                raise

                            # Build TransactionEvent(Started) driven by RemoteStart.
                            remote_start_id = cp._remote_start_id
                            remote_start_seen_utc = cp._remote_start_seen_utc
                            remote_start_evse_id = cp._remote_start_evse_id or 1
                            remote_start_id_token = cp._remote_start_id_token

                            tx_id = (cfg.poc_transaction_id or "").strip()
                            if not tx_id:
                                tx_id = (
                                    f"RS_{remote_start_id}"
                                    if remote_start_id
                                    else uuid.uuid4().hex
                                )
                            tx_id = tx_id[:36]

                            started_ts = utc_now_iso()
                            started_req = call.TransactionEvent(
                                event_type=enums.TransactionEventEnumType.started,
                                timestamp=started_ts,
                                trigger_reason=enums.TriggerReasonEnumType.remote_start,
                                seq_no=1,
                                transaction_info=dt.TransactionType(
                                    transaction_id=tx_id
                                ),
                                evse=dt.EVSEType(
                                    id=int(remote_start_evse_id), connector_id=1
                                ),
                                id_token=remote_start_id_token,
                            )
                            await _send_safe(
                                cp, started_req, "TransactionEvent(Started)"
                            )
                            notes.append(
                                "phase14: started_trigger_reason=RemoteStart "
                                f"tx_id={tx_id} remote_start_id={remote_start_id} "
                                f"seen_utc={remote_start_seen_utc}"
                            )
                            # Minimal Phase-1.4(A): finish after Started evidence.
                            await _send(cp, call.Heartbeat(), "Heartbeat")
                            return _final_report(finished=utc_now_iso())
                        else:

                            seq_no = 1
                            # Keep transactionId short (CSMS/lib constraints vary); stable for this run.
                            tx_id = (cfg.poc_transaction_id or uuid.uuid4().hex).strip()
                            if not tx_id:
                                tx_id = uuid.uuid4().hex
                            tx_id = tx_id[:36]

                            id_token = dt.IdTokenType(
                                id_token=cfg.id_token,
                                type=enums.IdTokenEnumType.central,
                            )

                            # Authorize(TEST001)
                            auth_req = call.Authorize(id_token=id_token)
                            auth_res = await _send_safe(cp, auth_req, "Authorize")
                            auth_summary = _response_summary(auth_res)
                            # Some CSMS policies may omit id_token_info in responses.
                            auth_has_id_token_info = bool(
                                getattr(auth_res, "id_token_info", None) is not None
                            )
                            auth_summary["id_token_info_present"] = (
                                auth_has_id_token_info
                            )
                            if auth_has_id_token_info:
                                iti = getattr(auth_res, "id_token_info", None)
                                if isinstance(iti, dict):
                                    auth_summary["id_token_status"] = iti.get("status")
                                else:
                                    auth_summary["id_token_status"] = getattr(
                                        iti, "status", None
                                    )
                            # Replace the last Authorize entry with enriched summary.
                            if messages and messages[-1].get("action") == "Authorize":
                                messages[-1]["response_summary"] = auth_summary

                        # TransactionEvent Started
                        started_ts = utc_now_iso()
                        started_req = call.TransactionEvent(
                            event_type=enums.TransactionEventEnumType.started,
                            timestamp=started_ts,
                            trigger_reason=enums.TriggerReasonEnumType.authorized,
                            seq_no=seq_no,
                            transaction_info=dt.TransactionType(transaction_id=tx_id),
                            evse=dt.EVSEType(id=1, connector_id=1),
                            id_token=id_token,
                        )
                        await _send_safe(cp, started_req, "TransactionEvent(Started)")
                        seq_no += 1

                        # MeterValues (3 samples, monotonic kWh)
                        energy_values: list[float] = []
                        base_kwh = 1000.0
                        for i in range(3):
                            if i > 0:
                                await asyncio.sleep(5)
                            kwh = base_kwh + (i + 1) * 0.01
                            energy_values.append(kwh)

                            mv_ts = utc_now_iso()
                            mv_req = call.MeterValues(
                                evse_id=1,
                                meter_value=[
                                    dt.MeterValueType(
                                        timestamp=mv_ts,
                                        sampled_value=[
                                            dt.SampledValueType(
                                                value=kwh,
                                                context=enums.ReadingContextEnumType.sample_periodic,
                                                measurand=enums.MeasurandEnumType.energy_active_import_register,
                                                unit_of_measure=dt.UnitOfMeasureType(
                                                    unit="kWh"
                                                ),
                                            )
                                        ],
                                    )
                                ],
                            )
                            await _send_safe(cp, mv_req, f"MeterValues[{i+1}]")

                            # Optional: TransactionEvent Updated after 2nd sample
                            if i == 1:
                                upd_ts = utc_now_iso()
                                upd_req = call.TransactionEvent(
                                    event_type=enums.TransactionEventEnumType.updated,
                                    timestamp=upd_ts,
                                    trigger_reason=enums.TriggerReasonEnumType.meter_value_periodic,
                                    seq_no=seq_no,
                                    transaction_info=dt.TransactionType(
                                        transaction_id=tx_id,
                                        charging_state=enums.ChargingStateEnumType.charging,
                                    ),
                                    evse=dt.EVSEType(id=1, connector_id=1),
                                    id_token=id_token,
                                    meter_value=mv_req.meter_value,
                                )
                                await _send_safe(
                                    cp, upd_req, "TransactionEvent(Updated)"
                                )
                                seq_no += 1

                        # TransactionEvent Ended (final meter + stoppedReason)
                        # Phase-1.3: map stoppedReason to stop source signal
                        remote_stop_seen = bool(
                            getattr(cp, "_remote_stop_event", None)
                            and cp._remote_stop_event.is_set()
                        )
                        remote_stop_tx_id = getattr(
                            cp, "_remote_stop_transaction_id", None
                        )
                        remote_stop_seen_utc = getattr(
                            cp, "_remote_stop_seen_utc", None
                        )

                        stop_source_cfg = (
                            (cfg.poc_stop_source or "auto").strip().lower()
                        )
                        if stop_source_cfg not in {"auto", "evdisconnected", "local"}:
                            stop_source_cfg = "auto"

                        # Optional wait window to allow inbound RequestStopTransaction.
                        if (
                            not remote_stop_seen
                            and stop_source_cfg == "auto"
                            and int(getattr(cfg, "poc_remote_stop_wait_seconds", 0)) > 0
                        ):
                            wait_s = int(
                                getattr(cfg, "poc_remote_stop_wait_seconds", 0)
                            )
                            try:
                                await asyncio.wait_for(
                                    cp._remote_stop_event.wait(), timeout=wait_s
                                )
                            except asyncio.TimeoutError:
                                pass
                            remote_stop_seen = cp._remote_stop_event.is_set()
                            remote_stop_tx_id = getattr(
                                cp, "_remote_stop_transaction_id", None
                            )
                            remote_stop_seen_utc = getattr(
                                cp, "_remote_stop_seen_utc", None
                            )

                        if remote_stop_seen:
                            ended_stopped_reason = enums.ReasonEnumType.remote
                            ended_trigger_reason = (
                                enums.TriggerReasonEnumType.remote_stop
                            )
                            notes.append(
                                "phase13: stop_source=remote "
                                f"inbound=RequestStopTransaction tx_id={remote_stop_tx_id} "
                                f"seen_utc={remote_stop_seen_utc}"
                            )
                        elif stop_source_cfg == "local":
                            ended_stopped_reason = enums.ReasonEnumType.local
                            ended_trigger_reason = (
                                enums.TriggerReasonEnumType.stop_authorized
                            )
                            notes.append("phase13: stop_source=local (simulated)")
                        else:
                            ended_stopped_reason = enums.ReasonEnumType.ev_disconnected
                            ended_trigger_reason = (
                                enums.TriggerReasonEnumType.ev_departed
                            )
                            notes.append(
                                "phase13: stop_source=evdisconnected (default)"
                            )

                        ended_ts = utc_now_iso()
                        final_kwh = energy_values[-1] if energy_values else base_kwh
                        ended_req = call.TransactionEvent(
                            event_type=enums.TransactionEventEnumType.ended,
                            timestamp=ended_ts,
                            trigger_reason=ended_trigger_reason,
                            seq_no=seq_no,
                            transaction_info=dt.TransactionType(
                                transaction_id=tx_id,
                                stopped_reason=ended_stopped_reason,
                            ),
                            evse=dt.EVSEType(id=1, connector_id=1),
                            id_token=id_token,
                            meter_value=[
                                dt.MeterValueType(
                                    timestamp=ended_ts,
                                    sampled_value=[
                                        dt.SampledValueType(
                                            value=final_kwh,
                                            context=enums.ReadingContextEnumType.transaction_end,
                                            measurand=enums.MeasurandEnumType.energy_active_import_register,
                                            unit_of_measure=dt.UnitOfMeasureType(
                                                unit="kWh"
                                            ),
                                        )
                                    ],
                                )
                            ],
                        )
                        await _send_safe(cp, ended_req, "TransactionEvent(Ended)")

                        # Local validations (evidence for Phase-1.2)
                        monotonic_energy_ok = all(
                            energy_values[i] < energy_values[i + 1]
                            for i in range(len(energy_values) - 1)
                        )
                        notes.append(
                            f"phase12: transaction_id={tx_id} seq_no_start=1 seq_no_end={seq_no}"
                        )
                        notes.append(
                            f"phase12: meter_kwh={energy_values} monotonic_ok={monotonic_energy_ok}"
                        )
                        notes.append(
                            f"phase13: ended_stopped_reason={ended_stopped_reason.value} "
                            f"trigger_reason={ended_trigger_reason.value}"
                        )
                    await _send(cp, call.Heartbeat(), "Heartbeat")
                finally:
                    runner.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await runner
            else:
                from ocpp.v16 import ChargePoint, call

                cp = ChargePoint(cfg.station_name, ws)
                runner = asyncio.create_task(cp.start())
                try:
                    await _send(
                        cp,
                        call.BootNotification(
                            charge_point_model=cfg.model,
                            charge_point_vendor=cfg.vendor_name,
                        ),
                        "BootNotification",
                    )
                    await _send(
                        cp,
                        call.StatusNotification(
                            connector_id=1,
                            error_code="NoError",
                            status="Available",
                            timestamp=utc_now_iso(),
                        ),
                        "StatusNotification",
                    )
                    await _send(cp, call.Heartbeat(), "Heartbeat")
                finally:
                    runner.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await runner
    except asyncio.TimeoutError as exc:
        protocol_timeout = True
        callerror = True
        notes.append(f"timeout: {exc}")
    except BaseException as exc:
        callerror = True
        notes.append(f"error: {exc}")

    return _final_report(finished=utc_now_iso())


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

        url = self.cfg.ocpp16_url
        headers = {
            "Authorization": basic_auth_header(
                self.cfg.station_name, self.cfg.station_password
            )
        }

        attempt = 0
        while True:
            try:
                async with websockets.connect(
                    url,
                    subprotocols=["ocpp1.6"],
                    additional_headers=headers,
                    ssl=ssl_if_needed(url),
                    open_timeout=10,
                    # Keepalive: helps prevent idle disconnects.
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as ws:
                    cp = ChargePoint(self.cfg.station_name, ws)
                    runner = asyncio.create_task(cp.start())
                    try:
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

                        await cp.call(
                            call.StatusNotification(
                                connector_id=1,
                                error_code="NoError",
                                status="Available",
                                timestamp=utc_now_iso(),
                            ),
                            suppress=False,
                            unique_id=str(uuid.uuid4()),
                        )
                        print("[OCPP] v16 StatusNotification(Available) sent")

                        hb_interval = int(
                            getattr(self.cfg, "heartbeat_override_seconds", 0) or 0
                        )
                        if hb_interval <= 0:
                            hb_interval = int(getattr(boot, "interval", None) or 300)
                        hb_interval = max(10, hb_interval)

                        if self.cfg.poc_mode:
                            print(
                                "[OCPP/PoC] OCPP 1.6J PoC not implemented yet "
                                "(Phase-1 priority is 2.0.1)."
                            )
                            return

                        if self.cfg.once_mode:
                            hb = await cp.call(
                                call.Heartbeat(),
                                suppress=False,
                                unique_id=str(uuid.uuid4()),
                            )
                            print(f"[OCPP] v16 Heartbeat current_time={hb.current_time}")
                            return

                        print(f"[OCPP] v16 daemon heartbeat_interval={hb_interval}s")
                        while True:
                            await asyncio.sleep(hb_interval)
                            hb = await cp.call(
                                call.Heartbeat(),
                                suppress=False,
                                unique_id=str(uuid.uuid4()),
                            )
                            print(
                                f"[OCPP] v16 Heartbeat current_time={hb.current_time}"
                            )
                    finally:
                        runner.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await runner

                # Normal websocket close: reset attempt and reconnect.
                attempt = 0
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                attempt += 1
                code = getattr(e, "code", None)
                reason = getattr(e, "reason", None)
                extra = ""
                if code is not None or reason is not None:
                    extra = f" code={code!r} reason={reason!r}"
                print(
                    f"[OCPP] v16 reconnect attempt={attempt} "
                    f"error_type={type(e).__name__} error={e}{extra}"
                )
                await asyncio.sleep(min(30.0, float(2 ** max(0, attempt))))


@dataclass(frozen=True)
class OcppRuntimeConfig:
    """
    Runtime configuration for the station client.

    Values are sourced from CLI args first, then env vars, then defaults.
    """

    station_name: str
    station_password: str

    ocpp201_url: str
    ocpp16_url: str

    primary: str  # "201" or "16"
    poc_mode: bool
    once_mode: bool

    vendor_name: str
    model: str
    id_token: str  # TEST001 (Phase-1)

    heartbeat_override_seconds: int

    # Read-only local API polling (Phase-1.5)
    local_api_base_url: str
    local_poll_enabled: bool
    local_poll_interval_seconds: int

    # Phase-1.3 PoC controls (stop source mapping evidence)
    # - auto: prefer Remote if RequestStopTransaction seen, else EVDisconnected
    # - evdisconnected: force EVDisconnected
    # - local: force Local (HMI/UI stop simulation)
    poc_stop_source: str
    # Optional wait window before ending the transaction to allow inbound remote stop.
    poc_remote_stop_wait_seconds: int
    # Optional fixed transactionId for PoC runs (helps CSMS trigger RequestStopTransaction).
    poc_transaction_id: str

    # Phase-1.4 PoC: wait for CSMS RequestStartTransaction and emit TransactionEvent(Started)
    poc_remote_start_enabled: bool
    poc_remote_start_wait_seconds: int

    # Phase-1.4 runbook (A/B/C): after Started, optionally accept SetChargingProfile and wait for
    # RequestStopTransaction, then emit TransactionEvent(Ended).
    poc_runbook_enabled: bool
    poc_runbook_wait_profile_seconds: int
    poc_runbook_wait_stop_seconds: int


def _env(name: str, default: str) -> str:
    val = os.getenv(name)
    return val if val is not None and val != "" else default


def _parse_bool(value: str, *, default: bool) -> bool:
    raw = (value or "").strip().lower()
    if raw in ("1", "true", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "no", "n", "off"):
        return False
    return default


def _load_config_defaults_from_json(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise ValueError("Invalid JSON in --config-json / OCPP_CONFIG_JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("OCPP config JSON must be a JSON object (dict)")
    return data


def _load_config_defaults_from_path(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise ValueError(f"OCPP config file not found: {path}") from exc
    except Exception as exc:
        raise ValueError(f"Failed to read OCPP config file: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError("OCPP config file must contain a JSON object (dict)")
    return data


def _load_config_defaults(args: argparse.Namespace) -> dict[str, Any]:
    """
    Optional provisioning defaults (secret-free).

    Supported sources (in increasing precedence):
      - file path: --config-path or env OCPP_CONFIG_PATH
      - inline JSON: --config-json or env OCPP_CONFIG_JSON

    Notes:
      - station password MUST NOT be provided via config JSON; use --station-password
        or env OCPP_STATION_PASSWORD.
      - Unknown keys are ignored.
    """
    merged: dict[str, Any] = {}

    raw_path = (
        getattr(args, "config_path", None) or os.getenv("OCPP_CONFIG_PATH") or ""
    ).strip()
    if raw_path:
        merged.update(_load_config_defaults_from_path(raw_path))

    raw_json = (
        getattr(args, "config_json", None) or os.getenv("OCPP_CONFIG_JSON") or ""
    ).strip()
    if raw_json:
        merged.update(_load_config_defaults_from_json(raw_json))

    allowed = {f.name for f in fields(OcppRuntimeConfig)} - {"station_password"}
    return {k: v for k, v in merged.items() if k in allowed}


def _bool_default_str(value: Any, *, fallback: bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and value in (0, 1):
        return "true" if bool(value) else "false"
    if isinstance(value, str) and value.strip() != "":
        return "true" if _parse_bool(value, default=fallback) else "false"
    return "true" if fallback else "false"


def _build_config(args: argparse.Namespace) -> OcppRuntimeConfig:
    defaults = _load_config_defaults(args)

    station_name = args.station_name or _env(
        "OCPP_STATION_NAME", str(defaults.get("station_name") or "ORGE_AC_001")
    )
    station_password = (
        args.station_password or os.getenv("OCPP_STATION_PASSWORD") or ""
    ).strip()
    if not station_password:
        raise ValueError(
            "Missing station password: provide --station-password or set OCPP_STATION_PASSWORD"
        )

    # URLs can be ws:// or wss://
    ocpp201_url = args.ocpp201_url or _env(
        "OCPP_201_URL",
        str(defaults.get("ocpp201_url") or f"wss://lixhium.xyz/ocpp/{station_name}"),
    )
    ocpp16_url = args.ocpp16_url or _env(
        "OCPP_16_URL",
        str(defaults.get("ocpp16_url") or f"wss://lixhium.xyz/ocpp16/{station_name}"),
    )

    primary = (
        (args.primary or _env("OCPP_PRIMARY", str(defaults.get("primary") or "201")))
        .strip()
        .lower()
    )
    if primary in {"2.0.1", "201", "v201", "ocpp201"}:
        primary = "201"
    elif primary in {"1.6", "1.6j", "16", "v16", "ocpp16"}:
        primary = "16"
    else:
        raise ValueError(f"Invalid primary OCPP version: {primary!r} (use 201 or 16)")

    return OcppRuntimeConfig(
        station_name=station_name,
        station_password=station_password,
        ocpp201_url=ocpp201_url,
        ocpp16_url=ocpp16_url,
        primary=primary,
        poc_mode=bool(args.poc),
        once_mode=bool(args.once),
        vendor_name=args.vendor_name
        or _env("OCPP_VENDOR", str(defaults.get("vendor_name") or "ORGE")),
        model=args.model or _env("OCPP_MODEL", str(defaults.get("model") or "AC-1")),
        id_token=args.id_token
        or _env("OCPP_TEST_ID_TOKEN", str(defaults.get("id_token") or "TEST001")),
        heartbeat_override_seconds=int(
            args.heartbeat_seconds
            or _env(
                "OCPP_HEARTBEAT_SECONDS",
                str(defaults.get("heartbeat_override_seconds") or "0"),
            )
        ),
        local_api_base_url=(
            args.local_api_base_url
            or _env(
                "OCPP_LOCAL_API_BASE_URL",
                str(defaults.get("local_api_base_url") or "http://localhost:8000"),
            )
        ).rstrip("/"),
        local_poll_enabled=_parse_bool(
            (
                args.local_poll_enabled
                if args.local_poll_enabled is not None
                else _env(
                    "OCPP_LOCAL_POLL_ENABLED",
                    _bool_default_str(
                        defaults.get("local_poll_enabled"), fallback=True
                    ),
                )
            ),
            default=True,
        ),
        local_poll_interval_seconds=int(
            args.local_poll_interval_seconds
            or _env(
                "OCPP_LOCAL_POLL_INTERVAL_SECONDS",
                str(defaults.get("local_poll_interval_seconds") or "10"),
            )
        ),
        poc_stop_source=(
            args.poc_stop_source
            or _env(
                "OCPP_POC_STOP_SOURCE", str(defaults.get("poc_stop_source") or "auto")
            )
        )
        .strip()
        .lower(),
        poc_remote_stop_wait_seconds=int(
            args.poc_remote_stop_wait_seconds
            or _env(
                "OCPP_POC_REMOTE_STOP_WAIT_SECONDS",
                str(defaults.get("poc_remote_stop_wait_seconds") or "0"),
            )
        ),
        poc_transaction_id=(
            args.poc_transaction_id
            or _env(
                "OCPP_POC_TRANSACTION_ID", str(defaults.get("poc_transaction_id") or "")
            )
        ).strip(),
        poc_remote_start_enabled=bool(args.poc_remote_start),
        poc_remote_start_wait_seconds=int(
            args.poc_remote_start_wait_seconds
            or _env(
                "OCPP_POC_REMOTE_START_WAIT_SECONDS",
                str(defaults.get("poc_remote_start_wait_seconds") or "120"),
            )
        ),
        poc_runbook_enabled=bool(args.poc_runbook),
        poc_runbook_wait_profile_seconds=int(
            args.poc_runbook_wait_profile_seconds
            or _env(
                "OCPP_POC_RUNBOOK_WAIT_PROFILE_SECONDS",
                str(defaults.get("poc_runbook_wait_profile_seconds") or "120"),
            )
        ),
        poc_runbook_wait_stop_seconds=int(
            args.poc_runbook_wait_stop_seconds
            or _env(
                "OCPP_POC_RUNBOOK_WAIT_STOP_SECONDS",
                str(defaults.get("poc_runbook_wait_stop_seconds") or "120"),
            )
        ),
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ocpp/main.py",
        description="OCPP station client runner (Phase-1, isolated process).",
    )

    p.add_argument(
        "--config-path",
        default=None,
        help="Optional JSON config file (secret-free defaults). Password must come from env/arg.",
    )
    p.add_argument(
        "--config-json",
        default=None,
        help="Optional JSON config string (secret-free defaults). Password must come from env/arg.",
    )

    p.add_argument("--station-name", default=None)
    p.add_argument("--station-password", default=None)
    p.add_argument("--ocpp201-url", default=None)
    p.add_argument("--ocpp16-url", default=None)
    p.add_argument(
        "--primary",
        default=None,
        help="Primary protocol version: 201 (OCPP 2.0.1) or 16 (OCPP 1.6J).",
    )

    p.add_argument("--vendor-name", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--id-token", default=None, help="Phase-1 test idToken/idTag.")

    p.add_argument(
        "--poc",
        action="store_true",
        help="Run Phase-1 PoC message sequence and exit (smoke test).",
    )
    p.add_argument(
        "--poc-stop-source",
        default=None,
        choices=["auto", "evdisconnected", "local"],
        help=(
            "Phase-1.3 PoC: stoppedReason mapping evidence. "
            "auto=Remote if inbound RequestStopTransaction seen, else EVDisconnected; "
            "evdisconnected=force EVDisconnected; local=force Local."
        ),
    )
    p.add_argument(
        "--poc-remote-stop-wait-seconds",
        default=None,
        help=(
            "Phase-1.3 PoC: optionally wait this many seconds before TransactionEvent(Ended) "
            "to allow inbound RequestStopTransaction. Default 0."
        ),
    )
    p.add_argument(
        "--poc-transaction-id",
        default=None,
        help=(
            "Phase-1.3 PoC: optional fixed transactionId to use for the run. "
            "This makes it easy for CSMS to send RequestStopTransaction(transactionId=...)."
        ),
    )
    p.add_argument(
        "--poc-remote-start",
        action="store_true",
        help=(
            "Phase-1.4 PoC: wait for inbound RequestStartTransaction and emit "
            "TransactionEvent(Started) with triggerReason=RemoteStart, then exit."
        ),
    )
    p.add_argument(
        "--poc-remote-start-wait-seconds",
        default=None,
        help=(
            "Phase-1.4 PoC: max seconds to wait for inbound RequestStartTransaction "
            "before failing the run. Default 120."
        ),
    )
    p.add_argument(
        "--poc-runbook",
        action="store_true",
        help=(
            "Phase-1.4 runbook: A=RequestStartTransaction → Started(RemoteStart), "
            "B=SetChargingProfile(Accepted), C=RequestStopTransaction → Ended(Remote/RemoteStop)."
        ),
    )
    p.add_argument(
        "--poc-runbook-wait-profile-seconds",
        default=None,
        help="Phase-1.4 runbook: max seconds to wait for SetChargingProfile after Started. Default 120.",
    )
    p.add_argument(
        "--poc-runbook-wait-stop-seconds",
        default=None,
        help="Phase-1.4 runbook: max seconds to wait for RequestStopTransaction after Started. Default 120.",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Connect, send Boot+Status(+1 Heartbeat), then exit (non-daemon smoke test).",
    )
    p.add_argument(
        "--heartbeat-seconds",
        default=None,
        help="Override Heartbeat interval seconds (0=use CSMS BootNotification interval).",
    )

    p.add_argument(
        "--local-api-base-url",
        default=None,
        help="Read-only local API base URL (default: http://localhost:8000).",
    )
    p.add_argument(
        "--local-poll-enabled",
        default=None,
        help="Enable read-only local API polling (true/false). Default true.",
    )
    p.add_argument(
        "--local-poll-interval-seconds",
        default=None,
        help="Local API polling interval seconds (default: 10).",
    )
    return p.parse_args(argv)


async def _run_primary_then_fallback(cfg: OcppRuntimeConfig) -> None:
    """
    Start station client.

    Phase-1 behavior:
    - Try primary once.
    - If primary fails to connect, try fallback once.
    - In PoC mode, the adapter runs the PoC sequence then exits.
    """
    # Local adapter import (kept inside function to avoid import-time surprises in some environments).
    from handlers import Ocpp201Adapter

    if cfg.primary == "201":
        try:
            adapter = Ocpp201Adapter(cfg)
            await adapter.run()
            return
        except BaseException as e:
            sys.stderr.write(f"[OCPP] Primary (2.0.1) failed: {e}\n")
            sys.stderr.flush()

        adapter = Ocpp16Adapter(cfg)
        await adapter.run()
        return

    # Primary 1.6J
    try:
        adapter = Ocpp16Adapter(cfg)
        await adapter.run()
        return
    except BaseException as e:
        sys.stderr.write(f"[OCPP] Primary (1.6J) failed: {e}\n")
        sys.stderr.flush()

    adapter = Ocpp201Adapter(cfg)
    await adapter.run()


async def _run_daemon_with_shutdown(cfg: OcppRuntimeConfig) -> None:
    """
    Run the daemon with graceful shutdown handling (systemd-friendly).

    Goal:
    - On SIGTERM/SIGINT: cancel the running adapter and exit cleanly.
    """
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    main_task = asyncio.create_task(_run_primary_then_fallback(cfg))
    stop_task = asyncio.create_task(stop_event.wait())
    done, _pending = await asyncio.wait(
        {main_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
    )

    if stop_task in done:
        print("[OCPP] shutdown requested; stopping daemon")
        main_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await main_task
        return

    stop_task.cancel()
    await main_task


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    cfg = _build_config(args)

    try:
        _verify_python_ocpp_package()
    except Exception as exc:
        sys.stderr.write(f"[OCPP] dependency check failed: {exc}\n")
        sys.stderr.flush()
        return 2

    # Safety: this runner is isolated. It must not be started implicitly.
    if cfg.once_mode:
        # IMPORTANT:
        # `--once` MUST output exactly one JSON object to stdout (CSMS ops tooling).
        # Do not print any other lines here.
        report = asyncio.run(_run_once_json(cfg))

        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2 if report.get("result", {}).get("callerror") else 0

    print("[OCPP] Station client starting (isolated process)")
    print(
        f"[OCPP] station_name={cfg.station_name} primary={cfg.primary} poc={cfg.poc_mode} once={cfg.once_mode}"
    )
    print(f"[OCPP] url_201={cfg.ocpp201_url}")
    print(f"[OCPP] url_16={cfg.ocpp16_url}")
    print(
        f"[OCPP] local_poll_enabled={cfg.local_poll_enabled} local_api_base_url={cfg.local_api_base_url} local_poll_interval_seconds={cfg.local_poll_interval_seconds}"
    )

    asyncio.run(_run_daemon_with_shutdown(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
