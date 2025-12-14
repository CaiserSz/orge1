#!/usr/bin/env python3
"""
Database Maintenance Script (Events Migration + Session Metrics Repair)
Created: 2025-12-10 07:40:00
Last Modified: 2025-12-14 21:55:00
Version: 1.2.0
Description:
  - Mevcut events JSON'ını session_events tablosuna migrate eder
  - (Opsiyonel) geçmiş session metriklerini düzeltir (avg/max/min power vb.)
  - (Opsiyonel) belirli bir tarihten önceki session'ları temizler (ABB dönemi temizliği)
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

# Proje root'unu path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.database import get_database
from api.logging_config import system_logger
from api.station_info import get_station_info


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _compute_energy_delta_kwh(
    session: Dict[str, Any],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Returns:
        (start_energy_kwh, end_energy_kwh, total_energy_kwh)
    """
    start_e = _safe_float(
        session.get("start_energy_kwh")
        or (session.get("metadata") or {}).get("start_energy_kwh")
    )
    end_e = _safe_float(
        session.get("end_energy_kwh")
        or (session.get("metadata") or {}).get("end_energy_kwh")
    )

    if start_e is not None and end_e is not None:
        total = max(0.0, end_e - start_e)
        return start_e, end_e, total

    total = _safe_float(
        session.get("total_energy_kwh")
        or (session.get("metadata") or {}).get("total_energy_kwh")
    )
    return start_e, end_e, (max(0.0, total) if total is not None else None)


def _compute_duration_seconds(session: Dict[str, Any]) -> Optional[int]:
    dur = session.get("charging_duration_seconds") or session.get("duration_seconds")
    try:
        if dur is None:
            return None
        return int(dur)
    except Exception:
        return None


def _needs_metrics_repair(session: Dict[str, Any]) -> bool:
    """
    Heuristic: CPV/PPV gibi ham değerlerin yazıldığı bozuk metrikleri tespit et.
    """
    bad_voltage_threshold = 500.0
    bad_power_threshold = (
        40.0  # 22kW AC üstü zaten anormal; bu eşik "bariz" durumlar içindir.
    )

    for key in ("avg_voltage_v", "max_voltage_v", "min_voltage_v"):
        v = _safe_float(session.get(key))
        if v is not None and v > bad_voltage_threshold:
            return True

    for key in ("avg_power_kw", "max_power_kw", "min_power_kw"):
        p = _safe_float(session.get(key))
        if p is not None and p > bad_power_threshold:
            return True

    return False


def migrate_events() -> int:
    db = get_database()
    return int(db.migrate_events_to_table())


def _parse_before_iso_to_epoch(before_iso: str) -> int:
    """
    Parse ISO timestamp (naive local or timezone-aware) to epoch seconds.

    Not: DB'deki start_time/end_time değerleri, kod tarafında `datetime.now().timestamp()`
    ile yazıldığı için "local timezone" bazlı epoch saniye formatındadır.
    """
    dt = datetime.fromisoformat(before_iso)
    return int(dt.timestamp())


def purge_sessions_before(before_iso: str, apply_changes: bool) -> int:
    """
    Purge sessions (and related session_events) before a cutoff timestamp.

    Amaç: ABB sayaç dönemindeki eski/bozuk/test session verilerini temizleyip,
    Acrel döneminde trend/istatistikleri daha anlamlı hale getirmek.
    """
    db = get_database()
    cutoff_ts = _parse_before_iso_to_epoch(before_iso)

    conn = sqlite3.connect(db.db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*), MIN(start_time), MAX(start_time) "
            "FROM sessions WHERE start_time < ?",
            (cutoff_ts,),
        )
        count, min_ts, max_ts = cursor.fetchone()
        candidate_count = int(count or 0)

        print("=" * 60)
        print("Purge Sessions Before Cutoff")
        print("=" * 60)
        print(f"before_iso={before_iso} cutoff_ts={cutoff_ts} apply={apply_changes}")
        print(
            f"candidates={candidate_count} "
            f"min_start={datetime.fromtimestamp(min_ts).isoformat() if min_ts else None} "
            f"max_start={datetime.fromtimestamp(max_ts).isoformat() if max_ts else None}"
        )

        cursor.execute(
            "SELECT session_id, start_time, status "
            "FROM sessions WHERE start_time < ? "
            "ORDER BY start_time DESC LIMIT 10",
            (cutoff_ts,),
        )
        sample = cursor.fetchall() or []
        if sample:
            print()
            print("Sample (latest 10 candidates):")
            for sid, st, status in sample:
                print(
                    f"- {sid} start={datetime.fromtimestamp(int(st)).isoformat()} status={status}"
                )

        if not apply_changes:
            print()
            print("ℹ️ Dry-run completed (no changes applied).")
            print("=" * 60)
            return 0

        # Foreign key cascade, PRAGMA foreign_keys'e bağlı olabilir; garanti olsun diye explicit delete.
        cursor.execute(
            "DELETE FROM session_events "
            "WHERE session_id IN (SELECT session_id FROM sessions WHERE start_time < ?)",
            (cutoff_ts,),
        )
        cursor.execute("DELETE FROM sessions WHERE start_time < ?", (cutoff_ts,))
        deleted_sessions = int(cursor.rowcount or 0)
        conn.commit()

        print()
        print(f"✅ Deleted sessions: {deleted_sessions}")
        print("=" * 60)
        return deleted_sessions
    finally:
        conn.close()


def repair_session_metrics(limit: int, apply_changes: bool) -> int:
    """
    Son N COMPLETED session için bariz hatalı güç/voltaj/akım metriklerini düzeltir.
    Meter delta + süre üzerinden avg power hesaplar, max/min'i avg'e set eder.
    """
    db = get_database()
    station_info = get_station_info() or {}
    per_kwh = _safe_float(station_info.get("price_per_kwh"))
    max_power_kw = _safe_float(station_info.get("max_power_kw")) or 22.0

    # Not: Bazı eski kayıtlar start_time alanını hatalı formatta (ms gibi) yazmış olabilir ve
    # "ORDER BY start_time DESC" ile en üste çıkıp hedef session'ları ilk N içinde gizleyebilir.
    # Bu nedenle burada "metrikleri bozuk olan kayıtları" SQL ile hedefli seçiyoruz.
    conn = sqlite3.connect(db.db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id
            FROM sessions
            WHERE status = 'COMPLETED'
              AND (
                COALESCE(avg_voltage_v, 0) > 500
                OR COALESCE(max_voltage_v, 0) > 500
                OR COALESCE(min_voltage_v, 0) > 500
                OR COALESCE(avg_power_kw, 0) > 40
                OR COALESCE(max_power_kw, 0) > 40
                OR COALESCE(min_power_kw, 0) > 40
              )
            ORDER BY start_time DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        session_ids = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()
    fixed = 0

    print("=" * 60)
    print("Session Metrics Repair")
    print("=" * 60)
    print(f"limit={limit} apply={apply_changes}")
    print()

    for session_id in session_ids:
        s = db.get_session(str(session_id))
        if not s:
            continue
        if not _needs_metrics_repair(s):
            continue

        start_e, end_e, total_e = _compute_energy_delta_kwh(s)
        duration_s = _compute_duration_seconds(s)
        if total_e is None or duration_s is None or duration_s <= 0:
            continue

        # Enerji plausibility kontrolü: sayaç reset/rollover veya register semantiği hatası
        # gibi durumlarda delta uçuk çıkabilir; otomatik düzeltme uygulama.
        duration_h = duration_s / 3600.0
        max_plausible_energy_kwh = max_power_kw * duration_h * 1.2  # %20 tolerans
        if total_e > max_plausible_energy_kwh:
            print(
                f"- {s.get('session_id')} SKIP energy_kwh={total_e:.3f} "
                f"> max_plausible={max_plausible_energy_kwh:.3f} (duration_s={duration_s})"
            )
            continue

        hours = duration_s / 3600.0
        avg_power_kw = round((total_e / hours), 3) if hours > 0 else None
        if avg_power_kw is None:
            continue

        # Voltaj/akım için en azından fiziksel aralıkta "türetilmiş" değerler yaz.
        # Not: geçmiş session'lar için faz bazlı meter örnekleri DB'de yok; bu nedenle estimate.
        assumed_voltage_v = 230.0
        est_current_a = round((avg_power_kw * 1000.0) / (assumed_voltage_v * 3.0), 2)

        metadata = dict(s.get("metadata") or {})
        metadata["metrics_repair_at"] = _now_iso()
        metadata["metrics_repair_method"] = "meter_delta_duration_estimate_vi"
        if per_kwh is not None:
            metadata["price_per_kwh"] = per_kwh
            metadata["total_cost"] = round(total_e * per_kwh, 2)

        print(
            f"- {s.get('session_id')} energy_kwh={total_e:.3f} duration_s={duration_s} "
            f"avg_power_kw={avg_power_kw:.3f} est_current_a={est_current_a:.2f}"
        )

        if not apply_changes:
            continue

        ok = db.update_session(
            session_id=str(s["session_id"]),
            total_energy_kwh=total_e,
            start_energy_kwh=start_e,
            end_energy_kwh=end_e,
            avg_power_kw=avg_power_kw,
            max_power_kw=avg_power_kw,
            min_power_kw=avg_power_kw,
            avg_voltage_v=assumed_voltage_v,
            max_voltage_v=assumed_voltage_v,
            min_voltage_v=assumed_voltage_v,
            avg_current_a=est_current_a,
            max_current_a=est_current_a,
            min_current_a=est_current_a,
            metadata=metadata,
        )
        if ok:
            fixed += 1

    print()
    print(f"✅ Fixed sessions: {fixed}" if apply_changes else "ℹ️ Dry-run completed.")
    print("=" * 60)
    return fixed


def main() -> None:
    """Maintenance script main fonksiyonu"""
    print("=" * 60)
    print("Database Maintenance Script")
    print("=" * 60)
    print()

    parser = argparse.ArgumentParser(
        description="Database maintenance operations for charger project"
    )
    sub = parser.add_subparsers(dest="command", required=False)

    p_migrate = sub.add_parser(
        "migrate-events", help="Migrate JSON events to session_events table"
    )
    p_migrate.set_defaults(command="migrate-events")

    p_fix = sub.add_parser(
        "repair-session-metrics",
        help="Repair invalid session metrics for recent sessions",
    )
    p_fix.add_argument(
        "--limit",
        type=int,
        default=50,
        help="How many recent COMPLETED sessions to scan",
    )
    p_fix.add_argument(
        "--apply", action="store_true", help="Apply changes to DB (default: dry-run)"
    )

    p_purge = sub.add_parser(
        "purge-sessions-before",
        help="Delete sessions (and session_events) older than a cutoff ISO timestamp",
    )
    p_purge.add_argument(
        "--before",
        dest="before_iso",
        default="2025-12-13T00:00:00",
        help="Cutoff ISO timestamp (naive local or timezone-aware)",
    )
    p_purge.add_argument("--apply", action="store_true", help="Apply deletions")

    args = parser.parse_args()

    if not args.command or args.command == "migrate-events":
        print("Mevcut events JSON'ını session_events tablosuna migrate ediliyor...")
        migrated_count = migrate_events()
        print()
        print("✅ Migration tamamlandı!")
        print(f"   Migrate edilen event sayısı: {migrated_count}")
        print()
        print("=" * 60)
        return

    if args.command == "repair-session-metrics":
        repair_session_metrics(limit=int(args.limit), apply_changes=bool(args.apply))
        return

    if args.command == "purge-sessions-before":
        purge_sessions_before(
            before_iso=str(args.before_iso), apply_changes=bool(args.apply)
        )
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMigration iptal edildi.")
        sys.exit(1)
    except Exception as e:
        system_logger.error(f"Migration hatası: {e}", exc_info=True)
        print(f"\n❌ Hata: {e}")
        sys.exit(1)
