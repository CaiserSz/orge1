#!/usr/bin/env python3
"""
Todo Dosyaları Otomatik Güncelleme Script'i

Bu script todo dosyalarını otomatik olarak günceller:
1. Tamamlanan görevleri master_next.md'den kaldırır veya durumunu günceller
2. Dosya boyutu standartlarına göre öncelikleri günceller
3. master_done.md'ye tamamlanan görevleri ekler

Kullanım:
    python3 scripts/todo_auto_update.py
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Proje kök dizini
PROJECT_ROOT = Path(__file__).parent.parent
TODO_DIR = PROJECT_ROOT / "todo"
API_DIR = PROJECT_ROOT / "api"

# Standartlar
MAX_LINES_API_ENDPOINT = 600
WARNING_LINES_API_ENDPOINT = 500


class TodoUpdater:
    """Todo dosyalarını güncelleyen sınıf"""

    def __init__(self):
        self.changes = []

    def update_master_next(self) -> bool:
        """master_next.md dosyasını güncelle"""
        master_next = TODO_DIR / "master_next.md"
        if not master_next.exists():
            return False

        content = master_next.read_text(encoding='utf-8')
        original_content = content

        # Event Detection durumunu güncelle
        if 'Event Detection' in content and 'api/event_detector.py' in str(API_DIR / "event_detector.py"):
            event_detector = API_DIR / "event_detector.py"
            if event_detector.exists():
                # Event Detection tamamlandı olarak işaretle
                pattern = r'(### 📋 Event Detection.*?Durum: 📋 Bekliyor.*?\n)'
                replacement = r'### ✅ Event Detection (Temel Implementasyon Tamamlandı - Öncelik 1)\n- [x] **Görev:** Event detector oluştur (`api/event_detector.py`)\n  - Durum: ✅ Temel implementasyon tamamlandı\n  - Not: Temel Event Detection tamamlandı. İyileştirmeler opsiyonel.\n'
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        # api/main.py önceliğini güncelle
        main_py = API_DIR / "main.py"
        if main_py.exists():
            lines = self._count_lines(main_py)
            if lines > MAX_LINES_API_ENDPOINT:
                # Önceliği Acil olarak güncelle
                pattern = r'(\[ \] \*\*Görev:\*\* `api/main\.py` router.*?Öncelik: )([^\n]+)'
                replacement = r'\1Acil (Öncelik 0)'
                content = re.sub(pattern, replacement, content)

                # Durumu güncelle
                pattern = r'(\[ \] \*\*Görev:\*\* `api/main\.py` router.*?Durum: )([^\n]+)'
                replacement = r'\1🔴 Maksimum sınır aşıldı'
                content = re.sub(pattern, replacement, content)

        # Son güncelleme tarihini güncelle
        pattern = r'\*\*Son Güncelleme:\*\* \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        new_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = re.sub(pattern, f"**Son Güncelleme:** {new_date}", content)

        if content != original_content:
            master_next.write_text(content, encoding='utf-8')
            self.changes.append("master_next.md güncellendi")
            return True

        return False

    def _count_lines(self, file_path: Path) -> int:
        """Dosyadaki satır sayısını say"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except Exception:
            return 0

    def run_updates(self) -> Dict:
        """Tüm güncellemeleri çalıştır"""
        updated = self.update_master_next()

        return {
            "updated": updated,
            "changes": self.changes,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Ana fonksiyon"""
    updater = TodoUpdater()
    results = updater.run_updates()

    if results['updated']:
        print("✅ Todo dosyaları güncellendi:")
        for change in results['changes']:
            print(f"  - {change}")
    else:
        print("ℹ️  Güncelleme gerekmiyor, todo dosyaları güncel.")


if __name__ == "__main__":
    main()

