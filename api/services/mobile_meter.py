"""
Mobile Meter/Alert Helpers
Created: 2025-12-13 18:50:00
Last Modified: 2025-12-13 21:45:00
Version: 1.0.1
Description: Mobil endpoint'ler için meter snapshot, measurements, trend ve alert yardımcıları.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from api.logging_config import system_logger
from api.meter import MeterReading
from api.session import SessionStatus

__all__ = [
    "build_device_block",
    "build_measurements",
    "build_trend_block",
    "collect_alerts",
    "collect_meter_snapshot",
]


def collect_meter_snapshot(get_meter_func: Callable[[], Any]) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "connected": False,
        "available": False,
        "reading": None,
        "last_update": None,
        "note": None,
    }
    try:
        meter = get_meter_func()
    except Exception as exc:
        system_logger.debug("Meter instance alınamadı: %s", exc)
        snapshot["note"] = "meter_not_configured"
        return snapshot

    if meter is None:
        snapshot["note"] = "meter_missing"
        return snapshot

    try:
        if hasattr(meter, "is_connected"):
            is_connected = bool(meter.is_connected())
            snapshot["connected"] = is_connected
            snapshot["available"] = True
            if not is_connected and hasattr(meter, "connect"):
                try:
                    meter.connect()
                    snapshot["connected"] = bool(meter.is_connected())
                except Exception:
                    pass

        reading = meter.read_all() if hasattr(meter, "read_all") else None
        if reading is None:
            snapshot["note"] = "no_reading"
        elif isinstance(reading, dict):
            snapshot["reading"] = reading
        elif getattr(reading, "is_valid", True):
            serialized = _serialize_meter_reading(reading)
            snapshot["reading"] = serialized
            snapshot["last_update"] = serialized.get("timestamp")
        else:
            snapshot["note"] = "invalid_reading"
    except Exception as exc:  # pragma: no cover
        system_logger.warning("Meter okuma hatası: %s", exc, exc_info=True)
        snapshot["note"] = str(exc)

    return snapshot


def build_device_block(
    station_info: Dict[str, Any], meter_snapshot: Dict[str, Any]
) -> Dict[str, Any]:
    return {
        "station_id": station_info.get("station_id"),
        "name": station_info.get("name"),
        "location": {
            "address": station_info.get("address"),
            "latitude": station_info.get("latitude"),
            "longitude": station_info.get("longitude"),
        },
        "connected": meter_snapshot.get("connected"),
        "available": meter_snapshot.get("available"),
        "last_update": meter_snapshot.get("last_update"),
        "meter_type": station_info.get("meter_type"),
        "max_power_kw": station_info.get("max_power_kw"),
        "max_current_amp": station_info.get("max_current_amp"),
        "price_per_kwh": station_info.get("price_per_kwh"),
    }


def build_measurements(reading: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not reading:
        return None

    phase_values = reading.get("phase_values") or {}
    voltage_phase = phase_values.get("voltage_v") or phase_values.get("voltage")
    current_phase = phase_values.get("current_a") or phase_values.get("current")
    power_phase = phase_values.get("power_kw") or phase_values.get("power")
    totals = reading.get("totals") or {}

    def _phase_or_total(source: Optional[Dict[str, Any]], default: Optional[float]):
        if isinstance(source, dict):
            return {
                "L1": source.get("L1") or source.get("l1"),
                "L2": source.get("L2") or source.get("l2"),
                "L3": source.get("L3") or source.get("l3"),
            }
        return {"total": default}

    if isinstance(power_phase, dict):
        power_total = power_phase.get("total") or reading.get("power_kw")
    else:
        power_total = reading.get("power_kw")

    # import/export ayrımı olan meter'larda import register'ını tercih et
    if isinstance(totals, dict):
        energy_import = totals.get("energy_import_kwh") or totals.get("energy_kwh")
    else:
        energy_import = reading.get("energy_kwh")

    return {
        "voltage_v": _phase_or_total(voltage_phase, reading.get("voltage_v")),
        "current_a": _phase_or_total(current_phase, reading.get("current_a")),
        "power_kw": {
            **(_phase_or_total(power_phase, power_total or reading.get("power_kw"))),
            "total": power_total or reading.get("power_kw"),
        },
        "energy_kwh": {
            "import": energy_import,
            "export": (
                totals.get("energy_export_kwh") if isinstance(totals, dict) else None
            ),
        },
        "frequency_hz": reading.get("frequency_hz"),
        "power_factor": reading.get("power_factor"),
        "timestamp": reading.get("timestamp"),
    }


def build_trend_block(
    session_manager: Any, measurements: Optional[Dict[str, Any]], *, max_fetch: int
) -> Dict[str, Any]:
    # Sadece "bugün" completed session'ları toplar
    today = _now().date()
    sessions = session_manager.get_sessions(
        limit=max_fetch, offset=0, status=SessionStatus.COMPLETED
    )
    energy_today = 0.0
    session_count = 0
    for sess in sessions:
        start_dt = _parse_datetime(sess.get("start_time"))
        if not start_dt or start_dt.date() != today:
            continue
        energy = sess.get("total_energy_kwh")
        if energy is None:
            energy = (sess.get("metadata") or {}).get("total_energy_kwh")
        try:
            energy_today += float(energy) if energy is not None else 0.0
        except (TypeError, ValueError):
            continue
        session_count += 1

    return {
        "power_kw_avg_5m": (measurements or {}).get("power_kw", {}).get("total"),
        "energy_kwh_today": round(energy_today, 3) if energy_today else 0.0,
        "sessions_today": session_count,
    }


def collect_alerts(get_alert_manager_func: Callable[[], Any]) -> List[Dict[str, Any]]:
    try:
        alert_manager = get_alert_manager_func()
    except Exception:
        return []

    if not alert_manager:
        return []

    alerts: List[Dict[str, Any]] = []
    try:
        for alert in alert_manager.get_active_alerts() or []:
            severity = getattr(alert, "severity", None)
            severity_value = getattr(severity, "value", severity)
            alerts.append(
                {
                    "name": getattr(alert, "name", None),
                    "message": getattr(alert, "message", None),
                    "severity": severity_value,
                    "timestamp": _to_iso(getattr(alert, "timestamp", None)),
                    "metadata": getattr(alert, "metadata", None),
                }
            )
    except Exception:
        return []

    return alerts


def _serialize_meter_reading(reading: MeterReading) -> Dict[str, Any]:
    phase_values = getattr(reading, "phase_values", None)
    totals = getattr(reading, "totals", None)
    return {
        "timestamp": _to_iso(getattr(reading, "timestamp", None)),
        "voltage_v": getattr(reading, "voltage_v", None),
        "current_a": getattr(reading, "current_a", None),
        "power_kw": getattr(reading, "power_kw", None),
        "power_w": getattr(reading, "power_w", None),
        "energy_kwh": getattr(reading, "energy_kwh", None),
        "frequency_hz": getattr(reading, "frequency_hz", None),
        "power_factor": getattr(reading, "power_factor", None),
        "phase_values": phase_values,
        "totals": totals,
    }


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _to_iso(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return value
    return str(value)


def _now() -> datetime:
    return datetime.now(timezone.utc)
