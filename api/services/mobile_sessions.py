"""
Mobile Session Helpers
Created: 2025-12-13 18:52:00
Last Modified: 2025-12-13 18:52:00
Version: 1.0.0
Description: Mobil endpoint'ler için session block, summary/detail serialization ve tarih filtreleme yardımcıları.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

__all__ = [
    "build_session_block",
    "filter_sessions_by_date",
    "now_iso",
    "parse_datetime",
    "serialize_session_detail",
    "serialize_session_summary",
]


def build_session_block(
    current_session: Optional[Dict[str, Any]],
    station_info: Dict[str, Any],
    measurements: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not current_session:
        return None

    metadata = current_session.get("metadata") or {}
    price_per_kwh = station_info.get("price_per_kwh")
    energy_kwh = _extract_energy_from_session(current_session)
    cost_total = (
        _round(energy_kwh * price_per_kwh, 2)
        if energy_kwh is not None and price_per_kwh is not None
        else None
    )
    start_dt = parse_datetime(current_session.get("start_time"))
    end_dt = parse_datetime(current_session.get("end_time")) or _now()
    duration_minutes = (
        (end_dt - start_dt).total_seconds() / 60 if start_dt and end_dt else None
    )

    power_total = (
        (measurements or {}).get("power_kw", {}).get("total") if measurements else None
    )

    return {
        "session_id": current_session.get("session_id"),
        "status": current_session.get("status"),
        "user_id": current_session.get("user_id"),
        "started_at": current_session.get("start_time"),
        "duration_minutes": _round(duration_minutes, 2) if duration_minutes else None,
        "energy_kwh": energy_kwh,
        "power_kw_current": power_total,
        "power_kw_average": current_session.get("avg_power_kw"),
        "estimated_finish": metadata.get("estimated_end_time"),
        "cost": {
            "currency": station_info.get("currency") or "TRY",
            "per_kwh": price_per_kwh,
            "estimated_total": cost_total,
        },
        "metadata": metadata,
    }


def serialize_session_summary(session: Dict[str, Any], price_per_kwh: Optional[float]):
    energy = _extract_energy_from_session(session)
    cost = (
        _round(energy * price_per_kwh, 2)
        if energy is not None and price_per_kwh is not None
        else None
    )
    duration_minutes = None
    start_dt = parse_datetime(session.get("start_time"))
    end_dt = parse_datetime(session.get("end_time"))
    if start_dt and end_dt:
        duration_minutes = (end_dt - start_dt).total_seconds() / 60

    metadata = session.get("metadata") or {}
    return {
        "session_id": session.get("session_id"),
        "started_at": session.get("start_time"),
        "ended_at": session.get("end_time"),
        "status": session.get("status"),
        "location": metadata.get("location") or metadata.get("station_name"),
        "energy_kwh": energy,
        "duration_minutes": _round(duration_minutes, 2) if duration_minutes else None,
        "cost": {
            "currency": metadata.get("currency") or "TRY",
            "total": cost,
            "per_kwh": price_per_kwh,
        },
    }


def serialize_session_detail(
    session: Dict[str, Any], station_info: Dict[str, Any]
) -> Dict[str, Any]:
    energy = _extract_energy_from_session(session)
    price_per_kwh = station_info.get("price_per_kwh")
    cost_total = (
        _round(energy * price_per_kwh, 2)
        if energy is not None and price_per_kwh is not None
        else None
    )
    start_dt = parse_datetime(session.get("start_time"))
    end_dt = parse_datetime(session.get("end_time"))
    duration_minutes = (
        (end_dt - start_dt).total_seconds() / 60 if start_dt and end_dt else None
    )

    snapshots = []
    for event in session.get("events", [])[:50]:
        status_data = event.get("data", {}).get("status") or event.get("status")
        snapshots.append(
            {
                "timestamp": event.get("timestamp"),
                "event_type": event.get("event_type"),
                "status": status_data,
            }
        )

    return {
        "session_id": session.get("session_id"),
        "status": session.get("status"),
        "started_at": session.get("start_time"),
        "ended_at": session.get("end_time"),
        "duration_minutes": _round(duration_minutes, 2) if duration_minutes else None,
        "energy_kwh": energy,
        "power_kw": {
            "max": session.get("max_power_kw"),
            "min": session.get("min_power_kw"),
            "avg": session.get("avg_power_kw"),
        },
        "current_a": {
            "max": session.get("max_current_a"),
            "min": session.get("min_current_a"),
            "avg": session.get("avg_current_a"),
            "set": session.get("set_current_a")
            or (session.get("metadata") or {}).get("set_current_a"),
        },
        "voltage_v": {
            "max": session.get("max_voltage_v"),
            "min": session.get("min_voltage_v"),
            "avg": session.get("avg_voltage_v"),
        },
        "cost": {
            "currency": station_info.get("currency") or "TRY",
            "per_kwh": price_per_kwh,
            "total": cost_total,
        },
        "metadata": session.get("metadata"),
        "events": session.get("events"),
        "snapshots": snapshots,
    }


def filter_sessions_by_date(
    sessions: List[Dict[str, Any]],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> List[Dict[str, Any]]:
    if not start_date and not end_date:
        return sessions

    end_bound = end_date
    if end_bound and end_bound.tzinfo is None:
        end_bound = end_bound.replace(tzinfo=None) + timedelta(microseconds=0)

    filtered: List[Dict[str, Any]] = []
    for session in sessions:
        start_dt = parse_datetime(session.get("start_time"))
        if not start_dt:
            continue
        if start_date and start_dt < start_date:
            continue
        if end_bound and start_dt > end_bound:
            continue
        filtered.append(session)
    return filtered


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def now_iso() -> str:
    return _now().isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _extract_energy_from_session(session: Dict[str, Any]) -> Optional[float]:
    energy = session.get("total_energy_kwh")
    if energy is None:
        energy = (session.get("metadata") or {}).get("total_energy_kwh")
    try:
        return float(energy) if energy is not None else None
    except (TypeError, ValueError):
        return None


def _round(value: Optional[float], digits: int) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None
