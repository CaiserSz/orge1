"""
OCPP Station Client Runner (Phase-1)

Created: 2025-12-16 01:20
Last Modified: 2025-12-18 00:20
Version: 0.5.0
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
import subprocess
import sys
import uuid
from dataclasses import dataclass, fields, is_dataclass
from typing import Any

import websockets
from handlers import Ocpp201Adapter
from states import (
    StationIdentity,
    basic_auth_header,
    serial_number_for_station_name,
    ssl_if_needed,
    utc_now_iso,
)


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


async def _run_once_json(cfg: Any) -> dict[str, Any]:
    # `--once` MUST output a single JSON object and MUST NOT include secrets.
    started_utc = utc_now_iso()
    finished_utc = started_utc
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
                    # Phase-1.2 extended single-run evidence (enabled via --poc + --once).
                    if cfg.poc_mode:
                        seq_no = 1
                        # Keep transactionId short (CSMS/lib constraints vary); stable for this run.
                        tx_id = uuid.uuid4().hex  # 32 chars

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
                        auth_summary["id_token_info_present"] = auth_has_id_token_info
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
                        ended_ts = utc_now_iso()
                        final_kwh = energy_values[-1] if energy_values else base_kwh
                        ended_req = call.TransactionEvent(
                            event_type=enums.TransactionEventEnumType.ended,
                            timestamp=ended_ts,
                            # Phase‑1.2 preference: default stop reason is EVDisconnected
                            # (Local: local UI/button, Remote: CSMS remote stop).
                            trigger_reason=enums.TriggerReasonEnumType.ev_departed,
                            seq_no=seq_no,
                            transaction_info=dt.TransactionType(
                                transaction_id=tx_id,
                                stopped_reason=enums.ReasonEnumType.ev_disconnected,
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
                            "phase12: ended_stopped_reason=EVDisconnected trigger_reason=EVDeparted"
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

    finished_utc = utc_now_iso()
    return {
        "station_name": cfg.station_name,
        "endpoint": url,
        "subprotocol": subprotocol,
        "run_started_utc": started_utc,
        "run_finished_utc": finished_utc,
        "auth": {"username": cfg.station_name},
        "result": {
            "callerror": bool(callerror),
            "protocol_timeout": bool(protocol_timeout),
            "notes": notes,
            "build": {
                "station_build_commit": _git_commit_short(),
                "ocpp_lib_version": _dist_version("ocpp"),
                "websockets_version": getattr(websockets, "__version__", None),
                "runtime_mode": "once",
                "phase": "phase-1.2" if bool(cfg.poc_mode) else "phase-1.1",
            },
            "inbound_calls": inbound,
        },
        "messages": messages,
    }


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

        async with websockets.connect(
            url,
            subprotocols=["ocpp1.6"],
            additional_headers=headers,
            ssl=ssl_if_needed(url),
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

                while True:
                    await asyncio.sleep(300)
                    await cp.call(
                        call.Heartbeat(), suppress=False, unique_id=str(uuid.uuid4())
                    )
            finally:
                runner.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runner


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


def _build_config(args: argparse.Namespace) -> OcppRuntimeConfig:
    station_name = args.station_name or _env("OCPP_STATION_NAME", "ORGE_AC_001")
    station_password = args.station_password or _env(
        "OCPP_STATION_PASSWORD", "temp_password_123"
    )

    # URLs can be ws:// or wss://
    ocpp201_url = args.ocpp201_url or _env(
        "OCPP_201_URL", f"wss://lixhium.xyz/ocpp/{station_name}"
    )
    ocpp16_url = args.ocpp16_url or _env(
        "OCPP_16_URL", f"wss://lixhium.xyz/ocpp16/{station_name}"
    )

    primary = (args.primary or _env("OCPP_PRIMARY", "201")).strip().lower()
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
        vendor_name=args.vendor_name or _env("OCPP_VENDOR", "ORGE"),
        model=args.model or _env("OCPP_MODEL", "AC-1"),
        id_token=args.id_token or _env("OCPP_TEST_ID_TOKEN", "TEST001"),
        heartbeat_override_seconds=int(
            args.heartbeat_seconds or _env("OCPP_HEARTBEAT_SECONDS", "0")
        ),
        local_api_base_url=(
            args.local_api_base_url
            or _env("OCPP_LOCAL_API_BASE_URL", "http://localhost:8000")
        ).rstrip("/"),
        local_poll_enabled=_parse_bool(
            (
                args.local_poll_enabled
                if args.local_poll_enabled is not None
                else _env("OCPP_LOCAL_POLL_ENABLED", "true")
            ),
            default=True,
        ),
        local_poll_interval_seconds=int(
            args.local_poll_interval_seconds
            or _env("OCPP_LOCAL_POLL_INTERVAL_SECONDS", "10")
        ),
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ocpp/main.py",
        description="OCPP station client runner (Phase-1, isolated process).",
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


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    cfg = _build_config(args)

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

    asyncio.run(_run_primary_then_fallback(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
