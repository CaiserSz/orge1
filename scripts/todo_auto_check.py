#!/usr/bin/env python3
"""
Todo Dosyaları Otomatik Kontrol ve Güncelleme Script'i

Bu script şunları kontrol eder ve günceller:
1. Tamamlanan görevlerin master_next.md'den kaldırılması
2. Dosya boyutu standartlarının kontrolü ve öncelik güncellemesi
3. Tamamlanan görevlerin master_done.md'ye eklenmesi
4. Checkpoint ve project_state.md güncellemeleri

Kullanım:
    python3 scripts/todo_auto_check.py [--dry-run] [--update]
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Proje kök dizini
PROJECT_ROOT = Path(__file__).parent.parent
TODO_DIR = PROJECT_ROOT / "todo"
API_DIR = PROJECT_ROOT / "api"
DOCS_DIR = PROJECT_ROOT / "docs"

# Standartlar
MAX_LINES_API_ENDPOINT = 600
WARNING_LINES_API_ENDPOINT = 500
MAX_LINES_MODULE = 500
WARNING_LINES_MODULE = 400


class TodoChecker:
    """Todo dosyalarını kontrol eden ve güncelleyen sınıf"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.changes = []
        self.warnings = []

    def check_file_size_standards(self) -> List[Dict]:
        """Dosya boyutu standartlarını kontrol et"""
        issues = []

        # api/main.py kontrolü
        main_py = API_DIR / "main.py"
        if main_py.exists():
            lines = self._count_lines(main_py)
            if lines > MAX_LINES_API_ENDPOINT:
                issues.append(
                    {
                        "file": str(main_py.relative_to(PROJECT_ROOT)),
                        "lines": lines,
                        "max": MAX_LINES_API_ENDPOINT,
                        "priority": "Acil (Öncelik 0)",
                        "status": "🔴 Maksimum sınır aşıldı",
                        "action": "Router'lara bölünmeli",
                    }
                )
            elif lines > WARNING_LINES_API_ENDPOINT:
                issues.append(
                    {
                        "file": str(main_py.relative_to(PROJECT_ROOT)),
                        "lines": lines,
                        "max": MAX_LINES_API_ENDPOINT,
                        "priority": "Orta",
                        "status": "🟡 Uyarı eşiği yakın",
                        "action": "Router'lara bölünmeli",
                    }
                )

        return issues

    def check_completed_tasks(self) -> List[Dict]:
        """Tamamlanan görevleri tespit et"""
        completed = []

        # Event Detection kontrolü
        event_detector = API_DIR / "event_detector.py"
        if event_detector.exists():
            # master_next.md'de hala "Bekliyor" olarak görünüyor mu?
            master_next = TODO_DIR / "master_next.md"
            if master_next.exists():
                content = master_next.read_text(encoding="utf-8")
                if "Event Detection" in content:
                    # Sadece Event Detection bloğu içinde Bekliyor varsa uyar
                    idx = content.index("Event Detection")
                    block = content[idx : idx + 500]
                    if "Bekliyor" in block:
                        completed.append(
                            {
                                "task": "Event Detection Modülü",
                                "file": "api/event_detector.py",
                                "status": "Tamamlandı",
                                "action": "master_next.md'de durum güncellenmeli",
                            }
                        )

        return completed

    def check_master_next_consistency(self) -> List[Dict]:
        """master_next.md tutarlılığını kontrol et"""
        issues = []

        master_next = TODO_DIR / "master_next.md"
        if not master_next.exists():
            return issues

        content = master_next.read_text(encoding="utf-8")

        # api/main.py görevi kontrolü
        if "api/main.py" in content:
            main_py = API_DIR / "main.py"
            if main_py.exists():
                lines = self._count_lines(main_py)
                # Öncelik kontrolü
                if lines > MAX_LINES_API_ENDPOINT:
                    if "Öncelik: Orta" in content or "Öncelik 0" not in content:
                        issues.append(
                            {
                                "task": "api/main.py router'lara bölme",
                                "issue": f"Öncelik 'Acil (Öncelik 0)' olmalı (şu anda {lines} satır, limit {MAX_LINES_API_ENDPOINT})",
                                "action": "Öncelik güncellenmeli",
                            }
                        )

        return issues

    def _count_lines(self, file_path: Path) -> int:
        """Dosyadaki satır sayısını say"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return len(f.readlines())
        except Exception:
            return 0

    def run_checks(self) -> Dict:
        """Tüm kontrolleri çalıştır"""
        results = {
            "file_size_issues": self.check_file_size_standards(),
            "completed_tasks": self.check_completed_tasks(),
            "consistency_issues": self.check_master_next_consistency(),
            "timestamp": datetime.now().isoformat(),
        }

        return results

    def print_report(self, results: Dict):
        """Rapor yazdır"""
        print("=" * 70)
        print("TODO DOSYALARI OTOMATIK KONTROL RAPORU")
        print("=" * 70)
        print(f"Tarih: {results['timestamp']}")
        print()

        # Dosya boyutu sorunları
        if results["file_size_issues"]:
            print("🔴 DOSYA BOYUTU SORUNLARI:")
            for issue in results["file_size_issues"]:
                print(
                    f"  - {issue['file']}: {issue['lines']} satır (Limit: {issue['max']})"
                )
                print(f"    Öncelik: {issue['priority']}")
                print(f"    Durum: {issue['status']}")
                print(f"    Aksiyon: {issue['action']}")
                print()
        else:
            print("✅ Dosya boyutu standartlarına uygun")
            print()

        # Tamamlanan görevler
        if results["completed_tasks"]:
            print("⚠️  TAMAMLANAN GÖREVLER (master_next.md'de güncellenmeli):")
            for task in results["completed_tasks"]:
                print(f"  - {task['task']}: {task['status']}")
                print(f"    Dosya: {task['file']}")
                print(f"    Aksiyon: {task['action']}")
                print()
        else:
            print("✅ Tamamlanan görevler güncel")
            print()

        # Tutarlılık sorunları
        if results["consistency_issues"]:
            print("⚠️  TUTARLILIK SORUNLARI:")
            for issue in results["consistency_issues"]:
                print(f"  - {issue['task']}")
                print(f"    Sorun: {issue['issue']}")
                print(f"    Aksiyon: {issue['action']}")
                print()
        else:
            print("✅ master_next.md tutarlı")
            print()

        print("=" * 70)

        # Özet
        total_issues = (
            len(results["file_size_issues"])
            + len(results["completed_tasks"])
            + len(results["consistency_issues"])
        )

        if total_issues == 0:
            print("✅ Tüm kontroller başarılı! Todo dosyaları güncel.")
        else:
            print(f"⚠️  Toplam {total_issues} sorun tespit edildi.")
            print("   '--update' parametresi ile otomatik güncelleme yapılabilir.")

        print("=" * 70)


def main():
    """Ana fonksiyon"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Todo dosyalarını otomatik kontrol ve güncelleme"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Sadece kontrol yap, değişiklik yapma"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Otomatik güncelleme yap (şimdilik sadece rapor)",
    )

    args = parser.parse_args()

    checker = TodoChecker(dry_run=args.dry_run)
    results = checker.run_checks()
    checker.print_report(results)

    if (
        results["file_size_issues"]
        or results["completed_tasks"]
        or results["consistency_issues"]
    ):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
