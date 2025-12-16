"""
OCPP Station Client Runner (Phase-1)

Created: 2025-12-16 01:20
Last Modified: 2025-12-16 15:57
Version: 0.4.1
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


async def _run_once_json(cfg: Any) -> dict[str, Any]:
    # `--once` MUST output a single JSON object and MUST NOT include secrets.
    started_utc = utc_now_iso()
    finished_utc = started_utc
    messages: list[dict[str, Any]] = []
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
                from ocpp.v201 import ChargePoint, call, call_result, enums
                from ocpp.v201 import datatypes as dt

                class StationCP(ChargePoint):
                    @on("GetBaseReport")
                    def on_get_base_report(
                        self, request_id: int, report_base: str, **kwargs
                    ):
                        return call_result.GetBaseReport(
                            status=enums.GenericDeviceModelStatusEnumType.accepted
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
    if cfg.once_mode and not cfg.poc_mode:
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
