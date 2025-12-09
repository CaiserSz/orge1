#!/usr/bin/env python3
"""
Events Migration Script
Created: 2025-12-10 07:40:00
Last Modified: 2025-12-10 07:40:00
Version: 1.0.0
Description: Mevcut events JSON'ını session_events tablosuna migrate eder
"""

import os
import sys

# Proje root'unu path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.database import get_database
from api.logging_config import system_logger


def main():
    """Migration script main fonksiyonu"""
    print("=" * 60)
    print("Events Migration Script")
    print("=" * 60)
    print()

    db = get_database()

    # Tüm session'ları migrate et
    print("Mevcut events JSON'ını session_events tablosuna migrate ediliyor...")
    migrated_count = db.migrate_events_to_table()

    print()
    print("✅ Migration tamamlandı!")
    print(f"   Migrate edilen event sayısı: {migrated_count}")
    print()
    print("=" * 60)


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
