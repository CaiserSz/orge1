"""
Database Models Module
Created: 2025-12-10 19:00:00
Last Modified: 2025-12-10 19:00:00
Version: 1.0.0
Description: Database row to dict conversion helpers
"""

import sqlite3
import json
from typing import Dict, Any
from datetime import datetime


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """
    Database row'unu dict'e dönüştür

    Args:
        row: SQLite row

    Returns:
        Session dict'i
    """
    # Timestamp'leri datetime'a çevir (INTEGER → datetime)
    start_time_dt = datetime.fromtimestamp(row["start_time"])
    end_time_dt = datetime.fromtimestamp(row["end_time"]) if row["end_time"] else None
    created_at_dt = datetime.fromtimestamp(row["created_at"])
    updated_at_dt = datetime.fromtimestamp(row["updated_at"])

    # Metadata'yı parse et
    metadata = json.loads(row["metadata"]) if row["metadata"] else {}

    result = {
        "session_id": row["session_id"],
        "start_time": start_time_dt.isoformat(),
        "end_time": end_time_dt.isoformat() if end_time_dt else None,
        "start_state": row["start_state"],
        "end_state": row["end_state"],
        "status": row["status"],
        "events": json.loads(row["events"]),
        "metadata": metadata,
        "created_at": created_at_dt.isoformat(),
        "updated_at": updated_at_dt.isoformat(),
        # Hesaplanan alanlar
        "duration_seconds": (
            (end_time_dt - start_time_dt).total_seconds()
            if end_time_dt
            else (
                datetime.now() - start_time_dt
            ).total_seconds()  # Aktif session için şu anki zaman
        ),
        "event_count": len(json.loads(row["events"])),
    }

    # user_id'yi metadata'dan veya database kolonundan al
    user_id = None
    if "user_id" in row.keys() and row["user_id"]:
        user_id = row["user_id"]
    elif "user_id" in metadata:
        user_id = metadata["user_id"]

    # user_id varsa ayrı bir field olarak ekle
    if user_id:
        result["user_id"] = user_id

    # Metrikleri ekle
    #
    # Not: API response standardizasyonu için, metrik kolonları mevcutsa anahtarların
    # response'ta her zaman bulunmasını istiyoruz (değer None olsa bile).
    # Bu sayede client tarafında "field missing" yerine "null" görülür ve schema tutarlı olur.
    metric_fields = [
        "duration_seconds",
        "charging_duration_seconds",
        "idle_duration_seconds",
        "total_energy_kwh",
        "start_energy_kwh",
        "end_energy_kwh",
        "max_power_kw",
        "avg_power_kw",
        "min_power_kw",
        "max_current_a",
        "avg_current_a",
        "min_current_a",
        "set_current_a",
        "max_voltage_v",
        "avg_voltage_v",
        "min_voltage_v",
        "event_count",
    ]

    for field in metric_fields:
        if field not in row.keys():
            continue
        if row[field] is not None:
            # DB'de kalıcı metrik varsa onu tercih et
            result[field] = row[field]
        else:
            # Kolon var ama değer yok: client schema'sı stabil kalsın diye anahtarı koru
            result.setdefault(field, None)

    return result


def event_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """
    Event row'unu dict'e dönüştür

    Args:
        row: SQLite row

    Returns:
        Event dict'i
    """
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "user_id": row.get("user_id"),
        "event_type": row["event_type"],
        "event_timestamp": datetime.fromtimestamp(row["event_timestamp"]).isoformat(),
        "from_state": row["from_state"],
        "to_state": row["to_state"],
        "from_state_name": row["from_state_name"],
        "to_state_name": row["to_state_name"],
        "current_a": row["current_a"],
        "voltage_v": row["voltage_v"],
        "power_kw": row["power_kw"],
        "event_data": json.loads(row["event_data"]) if row["event_data"] else None,
        "status_data": (json.loads(row["status_data"]) if row["status_data"] else None),
        "created_at": datetime.fromtimestamp(row["created_at"]).isoformat(),
    }
