#!/usr/bin/env python3
"""
Session Log Export Script
Created: 2025-12-12 05:55:00
Last Modified: 2025-12-12 05:55:00
Version: 1.0.0
Description: Belirli bir session_id için session.log ve SQLite kayıtlarını dışa aktarır.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
LOG_FILE = PROJECT_ROOT / "logs" / "session.log"
DB_PATH = PROJECT_ROOT / "data" / "sessions.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Session loglarını ve SQLite kayıtlarını dışa aktar.",
    )
    parser.add_argument("session_id", help="İncelenecek session UUID")
    parser.add_argument(
        "--format",
        choices=("json", "csv"),
        default="json",
        help="Çıktı formatı (varsayılan: json)",
    )
    parser.add_argument(
        "--output",
        help="Çıktı dosyası yolu (boş bırakılırsa stdout'a yazılır)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="JSON çıktısını pretty-print formatında üret",
    )
    return parser.parse_args()


def read_session_logs(session_id: str) -> List[Dict[str, Any]]:
    if not LOG_FILE.exists():
        return []

    snapshots: List[Dict[str, Any]] = []
    with LOG_FILE.open("r", encoding="utf-8") as log_file:
        for line in log_file:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if str(entry.get("session_id")) == session_id:
                entry["record_type"] = "log_snapshot"
                snapshots.append(entry)

    return snapshots


def read_session_from_db(
    session_id: str,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    if not DB_PATH.exists():
        return None, []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        session_row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if session_row:
            session_record = dict(session_row)
            session_record["record_type"] = "db_session"
        else:
            session_record = None

        event_rows = conn.execute(
            """
            SELECT *
            FROM session_events
            WHERE session_id = ?
            ORDER BY event_timestamp ASC
            """,
            (session_id,),
        ).fetchall()
        events = [dict(row) | {"record_type": "db_event"} for row in event_rows]
        return session_record, events
    except sqlite3.OperationalError:
        return None, []
    finally:
        conn.close()


def build_json_report(
    session_id: str,
    session_record: Optional[Dict[str, Any]],
    events: List[Dict[str, Any]],
    snapshots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "session": session_record,
        "db_events": events,
        "log_snapshots": snapshots,
        "counts": {
            "db_events": len(events),
            "log_snapshots": len(snapshots),
        },
    }


def export_json(report: Dict[str, Any], output: Optional[str], pretty: bool) -> None:
    payload = json.dumps(report, indent=2 if pretty else None, ensure_ascii=False)
    if output:
        Path(output).write_text(payload, encoding="utf-8")
    else:
        print(payload)


def export_csv(
    rows: List[Dict[str, Any]],
    output: Optional[str],
) -> None:
    if not rows:
        rows = [{"record_type": "info", "message": "Kayıt bulunamadı"}]

    fieldnames = sorted({key for row in rows for key in row.keys()})
    out_file = open(output, "w", encoding="utf-8", newline="") if output else None
    writer = csv.DictWriter(out_file or sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    if out_file:
        out_file.close()


def main() -> None:
    args = parse_args()
    session_record, db_events = read_session_from_db(args.session_id)
    snapshots = read_session_logs(args.session_id)

    if args.format == "json":
        report = build_json_report(
            args.session_id, session_record, db_events, snapshots
        )
        export_json(report, args.output, args.pretty)
    else:
        combined_rows: List[Dict[str, Any]] = []
        if session_record:
            combined_rows.append(session_record)
        combined_rows.extend(db_events)
        combined_rows.extend(snapshots)
        export_csv(combined_rows, args.output)


if __name__ == "__main__":
    main()
