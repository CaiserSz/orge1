"""
OCPP Station State Helpers (Phase-1)

Created: 2025-12-16 01:20
Last Modified: 2025-12-16 07:22
Version: 0.2.1
Description:
  Shared datatypes and helper utilities for the station OCPP client.
  This module intentionally contains helpers to keep `ocpp/handlers.py` within
  code size standards without creating new files/folders.
"""

from __future__ import annotations

import asyncio
import base64
import json
import ssl
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional


@dataclass(frozen=True)
class StationIdentity:
    """
    Minimal identity fields used in BootNotification and logging.

    Note:
      Phase-1 focuses on single-connector AC station `ORGE_AC_001`.
      These values are not sourced from the FastAPI runtime to keep isolation.
    """

    station_name: str
    vendor_name: str
    model: str
    firmware_version: str


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def basic_auth_header(station_name: str, password: str) -> str:
    raw = f"{station_name}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def ssl_if_needed(url: str) -> Optional[ssl.SSLContext]:
    return ssl.create_default_context() if url.lower().startswith("wss://") else None


def safe_float(value: Any) -> Optional[float]:
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


async def http_get_json(url: str, *, timeout_seconds: float = 2.0) -> Optional[dict]:
    return await asyncio.to_thread(
        _http_get_json_sync, url, timeout_seconds=timeout_seconds
    )


def serial_number_for_station_name(station_name: str) -> str:
    """
    OCPP v201 `chargingStation.serialNumber` has a max length constraint.

    Phase-1: derive it from station_name but truncate to keep python-ocpp
    schema validators happy.
    """
    s = (station_name or "").strip()
    if not s:
        return "UNKNOWN"
    return s[:25]


def derive_connector_status_label_from_station_payload(
    payload: Optional[dict],
) -> Optional[str]:
    """
    Map local `/api/station/status` JSON -> connector status label.

    Returns one of: available | occupied | reserved | faulted | unavailable
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
        return "faulted"
    if state_name_s in {"CHARGING", "PAUSED"}:
        return "occupied"
    if state_name_s in {"READY", "EV_CONNECTED"}:
        return "reserved"
    if state_name_s in {"CABLE_DETECT"}:
        return "occupied"
    if state_name_s in {"IDLE"}:
        return "available"

    if availability_s == "fault":
        return "faulted"
    if availability_s == "busy":
        return "occupied"
    if availability_s == "reserved":
        return "reserved"
    if availability_s == "available":
        return "available"

    return "unavailable"


def extract_energy_import_kwh_from_meter_payload(
    payload: Optional[dict],
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
        v = safe_float(totals.get("energy_import_kwh"))
        if v is not None:
            return v
        v = safe_float(totals.get("energy_kwh"))
        if v is not None:
            return v
        v = safe_float(totals.get("energy_total_kwh"))
        if v is not None:
            return v

    return safe_float(data.get("energy_kwh"))


def extract_current_session_from_sessions_current_payload(
    payload: Optional[dict],
) -> Optional[dict]:
    """
    Extract session dict from `/api/sessions/current` endpoint payload.

    Expected:
      { success: bool, session: dict | None, ... }
    """
    if not payload or not isinstance(payload, dict):
        return None
    session = payload.get("session")
    if isinstance(session, dict):
        return session
    return None


@dataclass
class LocalApiPollerConfig:
    base_url: str
    poll_interval_seconds: int = 10


@dataclass
class LocalApiPollerState:
    last_status_label: Optional[str] = "available"
    last_energy_kwh: Optional[float] = None
    active_session_id: Optional[str] = None
    active_session_status: Optional[str] = None


class LocalApiPoller:
    """
    Read-only poller that consumes local API endpoints and emits high-level events.

    It does NOT talk to ESP32 directly and does NOT mutate the local API.
    """

    def __init__(self, cfg: LocalApiPollerConfig):
        self.cfg = cfg
        self.state = LocalApiPollerState()

        self.cfg.base_url = self.cfg.base_url.rstrip("/")
        self.cfg.poll_interval_seconds = max(
            5, int(self.cfg.poll_interval_seconds or 10)
        )

        self.station_status_url = f"{self.cfg.base_url}/api/station/status"
        self.meter_reading_url = f"{self.cfg.base_url}/api/meter/reading"
        self.sessions_current_url = f"{self.cfg.base_url}/api/sessions/current"

    async def run(
        self,
        *,
        on_status_change: Callable[[str], Awaitable[None]],
        on_energy_update: Callable[[float], Awaitable[None]],
        on_session_started: Callable[[str, Optional[float]], Awaitable[None]],
        on_session_ended: Callable[
            [str, Optional[float], Optional[str]], Awaitable[None]
        ],
    ) -> None:
        while True:
            try:
                station_payload = await http_get_json(
                    self.station_status_url, timeout_seconds=2.0
                )
                status_label = derive_connector_status_label_from_station_payload(
                    station_payload
                )
                if status_label and status_label != self.state.last_status_label:
                    await on_status_change(status_label)
                    self.state.last_status_label = status_label

                meter_payload = await http_get_json(
                    self.meter_reading_url, timeout_seconds=2.0
                )
                energy_kwh = extract_energy_import_kwh_from_meter_payload(meter_payload)
                if energy_kwh is not None:
                    # Monotonic guard
                    if (
                        self.state.last_energy_kwh is not None
                        and energy_kwh + 1e-6 < self.state.last_energy_kwh
                    ):
                        # Keep last_energy_kwh unchanged; skip emit
                        pass
                    else:
                        if (
                            self.state.last_energy_kwh is None
                            or abs(energy_kwh - self.state.last_energy_kwh) >= 0.01
                        ):
                            await on_energy_update(energy_kwh)
                        self.state.last_energy_kwh = energy_kwh

                sessions_payload = await http_get_json(
                    self.sessions_current_url, timeout_seconds=2.0
                )
                session = extract_current_session_from_sessions_current_payload(
                    sessions_payload
                )

                new_session_id = None
                new_session_status = None
                if session:
                    new_session_id = session.get("session_id")
                    new_session_status = session.get("status")
                    # Only treat ACTIVE as an active charging transaction for Phase-1
                    if new_session_status != "ACTIVE":
                        new_session_id = None

                # Transition detection
                if self.state.active_session_id is None and new_session_id:
                    self.state.active_session_id = str(new_session_id)
                    self.state.active_session_status = str(new_session_status)
                    await on_session_started(
                        self.state.active_session_id, self.state.last_energy_kwh
                    )
                elif self.state.active_session_id and not new_session_id:
                    old_id = self.state.active_session_id
                    old_status = self.state.active_session_status
                    self.state.active_session_id = None
                    self.state.active_session_status = None
                    await on_session_ended(
                        old_id, self.state.last_energy_kwh, old_status
                    )
                elif (
                    self.state.active_session_id
                    and new_session_id
                    and str(new_session_id) != self.state.active_session_id
                ):
                    old_id = self.state.active_session_id
                    old_status = self.state.active_session_status
                    self.state.active_session_id = str(new_session_id)
                    self.state.active_session_status = str(new_session_status)
                    await on_session_ended(
                        old_id, self.state.last_energy_kwh, old_status
                    )
                    await on_session_started(
                        self.state.active_session_id, self.state.last_energy_kwh
                    )

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Must never break the daemon; ignore and retry next loop.
                print(f"[OCPP] local poller error: {exc}")

            await asyncio.sleep(self.cfg.poll_interval_seconds)


async def run_poc_v201(
    cp: Any,
    *,
    identity: StationIdentity,
    id_token: str,
    call: Any,
    datatypes: Any,
    enums: Any,
) -> None:
    """
    Phase-1 PoC message sequence for OCPP 2.0.1 (v201).

    BootNotification → Authorize(TEST001) → StatusNotification →
    TransactionEvent(started/ended) → MeterValues(Energy.Active.Import.Register)
    """

    def _energy_mv(kwh: float) -> Any:
        return datatypes.MeterValueType(
            timestamp=utc_now_iso(),
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

    async def _do(label: str, payload: Any) -> Any:
        uid = str(uuid.uuid4())
        ts = utc_now_iso()
        res = await cp.call(payload, suppress=False, unique_id=uid)
        print(f"[OCPP/PoC] {label} utc={ts} unique_id={uid} result={res}")
        return res

    await _do(
        "BootNotification",
        call.BootNotification(
            charging_station=datatypes.ChargingStationType(
                vendor_name=identity.vendor_name,
                model=identity.model,
                serial_number=serial_number_for_station_name(identity.station_name),
                firmware_version=identity.firmware_version,
            ),
            reason=enums.BootReasonEnumType.power_up,
        ),
    )

    token_obj = datatypes.IdTokenType(
        id_token=id_token, type=enums.IdTokenEnumType.central
    )
    auth_res = await _do("Authorize", call.Authorize(id_token=token_obj))
    print(
        f"[OCPP/PoC] Authorize is SoT, response.id_token_info={getattr(auth_res, 'id_token_info', None)}"
    )

    await _do(
        "StatusNotification(Available)",
        call.StatusNotification(
            timestamp=utc_now_iso(),
            connector_status=enums.ConnectorStatusEnumType.available,
            evse_id=1,
            connector_id=1,
        ),
    )

    tx_id = str(uuid.uuid4())
    evse = datatypes.EVSEType(id=1, connector_id=1)

    started_res = await _do(
        "TransactionEvent(Started)",
        call.TransactionEvent(
            event_type=enums.TransactionEventEnumType.started,
            timestamp=utc_now_iso(),
            trigger_reason=enums.TriggerReasonEnumType.authorized,
            seq_no=1,
            transaction_info=datatypes.TransactionType(transaction_id=tx_id),
            evse=evse,
            id_token=token_obj,
            meter_value=[_energy_mv(1000.00)],
        ),
    )
    print(
        "[OCPP/PoC] TransactionEvent response id_token_info expected None, got:",
        getattr(started_res, "id_token_info", None),
    )

    await _do(
        "MeterValues(Energy.Active.Import.Register)",
        call.MeterValues(evse_id=1, meter_value=[_energy_mv(1000.10)]),
    )

    ended_res = await _do(
        "TransactionEvent(Ended)",
        call.TransactionEvent(
            event_type=enums.TransactionEventEnumType.ended,
            timestamp=utc_now_iso(),
            trigger_reason=enums.TriggerReasonEnumType.ev_departed,
            seq_no=2,
            transaction_info=datatypes.TransactionType(
                transaction_id=tx_id,
                stopped_reason=enums.ReasonEnumType.ev_disconnected,
            ),
            evse=evse,
            id_token=token_obj,
            meter_value=[_energy_mv(1000.20)],
        ),
    )
    print(
        "[OCPP/PoC] TransactionEvent(Ended) response id_token_info expected None, got:",
        getattr(ended_res, "id_token_info", None),
    )
