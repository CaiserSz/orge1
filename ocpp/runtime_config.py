"""
OCPP Station Runtime Configuration (Phase-1)

Created: 2025-12-21 20:10
Last Modified: 2025-12-21 20:10
Version: 0.1.0
Description:
  Secret-safe runtime configuration utilities for the OCPP station client.
  Values are sourced from CLI args first, then env vars, then defaults.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, fields
from typing import Any


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

    raw_path = (getattr(args, "config_path", None) or os.getenv("OCPP_CONFIG_PATH") or "").strip()
    if raw_path:
        merged.update(_load_config_defaults_from_path(raw_path))

    raw_json = (getattr(args, "config_json", None) or os.getenv("OCPP_CONFIG_JSON") or "").strip()
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


def build_config(args: argparse.Namespace) -> OcppRuntimeConfig:
    defaults = _load_config_defaults(args)

    station_name = args.station_name or _env(
        "OCPP_STATION_NAME", str(defaults.get("station_name") or "ORGE_AC_001")
    )
    station_password = (args.station_password or os.getenv("OCPP_STATION_PASSWORD") or "").strip()
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

    primary = (args.primary or _env("OCPP_PRIMARY", str(defaults.get("primary") or "201"))).strip().lower()
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
        vendor_name=args.vendor_name or _env("OCPP_VENDOR", str(defaults.get("vendor_name") or "ORGE")),
        model=args.model or _env("OCPP_MODEL", str(defaults.get("model") or "AC-1")),
        id_token=args.id_token or _env("OCPP_TEST_ID_TOKEN", str(defaults.get("id_token") or "TEST001")),
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
                    _bool_default_str(defaults.get("local_poll_enabled"), fallback=True),
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
        poc_stop_source=(args.poc_stop_source or _env("OCPP_POC_STOP_SOURCE", str(defaults.get("poc_stop_source") or "auto")))
        .strip()
        .lower(),
        poc_remote_stop_wait_seconds=int(
            args.poc_remote_stop_wait_seconds
            or _env(
                "OCPP_POC_REMOTE_STOP_WAIT_SECONDS",
                str(defaults.get("poc_remote_stop_wait_seconds") or "0"),
            )
        ),
        poc_transaction_id=(args.poc_transaction_id or _env("OCPP_POC_TRANSACTION_ID", str(defaults.get("poc_transaction_id") or ""))).strip(),
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


