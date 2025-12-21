"""
OCPP --once JSON Evidence (Phase-1)

Created: 2025-12-21 20:25
Last Modified: 2025-12-21 20:25
Version: 0.1.0
Description:
  Implements `ocpp/main.py --once` as a single JSON output (secret-free).
  The report is designed for ops/CSMS correlation and must not print any secrets.
"""

from __future__ import annotations

import asyncio
import contextlib
import subprocess
import uuid
from dataclasses import fields, is_dataclass
from typing import Any

import websockets
from states import basic_auth_header, ssl_if_needed, utc_now_iso


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


class OnceContext:
    def __init__(self, *, cfg: Any, url: str, subprotocol: str):
        self.cfg = cfg
        self.url = url
        self.subprotocol = subprotocol
        self.started_utc = utc_now_iso()
        self.messages: list[dict[str, Any]] = []
        self.inbound: list[dict[str, Any]] = []
        self.notes: list[str] = []
        self.callerror = False
        self.protocol_timeout = False

    def response_summary(self, obj: Any) -> dict[str, Any]:
        return _response_summary(obj)

    async def send(self, cp: Any, req: Any, action: str) -> None:
        uid = str(uuid.uuid4())
        ts = utc_now_iso()
        res = await cp.call(req, suppress=False, unique_id=uid)
        self.messages.append(
            {
                "action": action,
                "utc": ts,
                "unique_id": uid,
                "request_keys": _dataclass_field_names(req),
                "response_summary": _response_summary(res),
            }
        )

    async def send_safe(self, cp: Any, req: Any, action: str) -> Any:
        """
        Send a CALL and always append a message entry.
        Returns response on success. Raises on error (after recording).
        """
        uid = str(uuid.uuid4())
        ts = utc_now_iso()
        try:
            res = await cp.call(req, suppress=False, unique_id=uid)
            self.messages.append(
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
            self.messages.append(
                {
                    "action": action,
                    "utc": ts,
                    "unique_id": uid,
                    "request_keys": _dataclass_field_names(req),
                    "response_summary": {"error": str(exc)},
                }
            )
            raise

    def final_report(self, *, finished_utc: str) -> dict[str, Any]:
        # `--once` MUST output a single JSON object and MUST NOT include secrets.
        cfg = self.cfg
        return {
            "station_name": getattr(cfg, "station_name", None),
            "endpoint": self.url,
            "subprotocol": self.subprotocol,
            "run_started_utc": self.started_utc,
            "run_finished_utc": finished_utc,
            "auth": {"username": getattr(cfg, "station_name", None)},
            "result": {
                "callerror": bool(self.callerror),
                "protocol_timeout": bool(self.protocol_timeout),
                "notes": self.notes,
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
                        else (
                            "phase-1.3"
                            if bool(getattr(cfg, "poc_mode", False))
                            else "phase-1.1"
                        )
                    ),
                },
                "inbound_calls": self.inbound,
            },
            "messages": self.messages,
        }


async def run_once_json(cfg: Any) -> dict[str, Any]:
    subprotocol = "ocpp2.0.1" if cfg.primary == "201" else "ocpp1.6"
    url = cfg.ocpp201_url if cfg.primary == "201" else cfg.ocpp16_url
    headers = {
        "Authorization": basic_auth_header(cfg.station_name, cfg.station_password)
    }

    ctx = OnceContext(cfg=cfg, url=url, subprotocol=subprotocol)

    try:
        async with websockets.connect(
            url,
            subprotocols=[subprotocol],
            additional_headers=headers,
            ssl=ssl_if_needed(url),
            open_timeout=10,
        ) as ws:
            if cfg.primary == "201":
                from once_v201 import run_once_v201

                await run_once_v201(ws=ws, cfg=cfg, ctx=ctx)
            else:
                from ocpp.v16 import ChargePoint, call

                cp = ChargePoint(cfg.station_name, ws)
                runner = asyncio.create_task(cp.start())
                try:
                    await ctx.send(
                        cp,
                        call.BootNotification(
                            charge_point_model=cfg.model,
                            charge_point_vendor=cfg.vendor_name,
                        ),
                        "BootNotification",
                    )
                    await ctx.send(
                        cp,
                        call.StatusNotification(
                            connector_id=1,
                            error_code="NoError",
                            status="Available",
                            timestamp=utc_now_iso(),
                        ),
                        "StatusNotification",
                    )
                    await ctx.send(cp, call.Heartbeat(), "Heartbeat")
                finally:
                    runner.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await runner
    except asyncio.TimeoutError as exc:
        ctx.protocol_timeout = True
        ctx.callerror = True
        ctx.notes.append(f"timeout: {exc}")
    except BaseException as exc:
        ctx.callerror = True
        ctx.notes.append(f"error: {exc}")

    return ctx.final_report(finished_utc=utc_now_iso())
