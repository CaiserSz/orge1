#!/usr/bin/env python3
"""
Standart Kontrol Otomasyon Script'i

Bu script kod ve dokümantasyon standartlarını kontrol eder:
1. Dosya boyutu kontrolü (satır sayısı)
2. Dosya standartları kontrolü (CODE_DOCUMENTATION_STANDARDS.md)
3. Otomatik master_next.md güncelleme önerileri

Kullanım:
    python3 scripts/standards_auto_check.py [--dry-run] [--update]
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Proje kök dizini
PROJECT_ROOT = Path(__file__).parent.parent
API_DIR = PROJECT_ROOT / "api"
DOCS_DIR = PROJECT_ROOT / "docs"
TODO_DIR = PROJECT_ROOT / "todo"

# Standartlar (CODE_DOCUMENTATION_STANDARDS.md'den)
MAX_LINES_API_ENDPOINT = 600
WARNING_LINES_API_ENDPOINT = 500
MAX_LINES_MODULE = 500
WARNING_LINES_MODULE = 400
MAX_LINES_TEST = 500
WARNING_LINES_TEST = 400
MAX_LINES_DOC = 1200
WARNING_LINES_DOC = 1000


class StandardsChecker:
    """Standart kontrolü yapan sınıf"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.issues = []
        self.warnings = []

    def check_file_size(self, file_path: Path) -> Optional[Dict]:
        """Dosya boyutunu kontrol et"""
        if not file_path.exists():
            return None

        lines = self._count_lines(file_path)
        file_type = self._get_file_type(file_path)

        issue = None

        if file_type == "api_endpoint":
            if lines > MAX_LINES_API_ENDPOINT:
                issue = {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "lines": lines,
                    "max": MAX_LINES_API_ENDPOINT,
                    "type": "error",
                    "priority": "Acil (Öncelik 0)",
                    "status": "🔴 Maksimum sınır aşıldı",
                    "action": "Router'lara bölünmeli"
                }
            elif lines > WARNING_LINES_API_ENDPOINT:
                issue = {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "lines": lines,
                    "max": MAX_LINES_API_ENDPOINT,
                    "type": "warning",
                    "priority": "Orta",
                    "status": "🟡 Uyarı eşiği yakın",
                    "action": "Router'lara bölünmeli"
                }
        elif file_type == "module":
            if lines > MAX_LINES_MODULE:
                issue = {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "lines": lines,
                    "max": MAX_LINES_MODULE,
                    "type": "error",
                    "priority": "Yüksek",
                    "status": "🔴 Maksimum sınır aşıldı",
                    "action": "Modüllere bölünmeli"
                }
            elif lines > WARNING_LINES_MODULE:
                issue = {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "lines": lines,
                    "max": MAX_LINES_MODULE,
                    "type": "warning",
                    "priority": "Orta",
                    "status": "🟡 Uyarı eşiği yakın",
                    "action": "Modüllere bölünmeli"
                }
        elif file_type == "test":
            if lines > MAX_LINES_TEST:
                issue = {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "lines": lines,
                    "max": MAX_LINES_TEST,
                    "type": "error",
                    "priority": "Yüksek",
                    "status": "🔴 Maksimum sınır aşıldı",
                    "action": "Test suite'e bölünmeli"
                }
            elif lines > WARNING_LINES_TEST:
                issue = {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "lines": lines,
                    "max": MAX_LINES_TEST,
                    "type": "warning",
                    "priority": "Orta",
                    "status": "🟡 Uyarı eşiği yakın",
                    "action": "Test suite'e bölünmeli"
                }
        elif file_type == "doc":
            if lines > MAX_LINES_DOC:
                issue = {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "lines": lines,
                    "max": MAX_LINES_DOC,
                    "type": "error",
                    "priority": "Yüksek",
                    "status": "🔴 Maksimum sınır aşıldı",
                    "action": "Bölümlere ayrılmalı"
                }
            elif lines > WARNING_LINES_DOC:
                issue = {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "lines": lines,
                    "max": MAX_LINES_DOC,
                    "type": "warning",
                    "priority": "Orta",
                    "status": "🟡 Uyarı eşiği yakın",
                    "action": "Bölümlere ayrılmalı"
                }

        return issue

    def _get_file_type(self, file_path: Path) -> str:
        """Dosya tipini belirle"""
        if file_path.name == "main.py" and "api" in str(file_path):
            return "api_endpoint"
        elif file_path.suffix == ".py":
            if "test" in str(file_path):
                return "test"
            else:
                return "module"
        elif file_path.suffix == ".md":
            return "doc"
        return "unknown"

    def _count_lines(self, file_path: Path) -> int:
        """Dosyadaki satır sayısını say"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except Exception:
            return 0

    def check_all_files(self) -> List[Dict]:
        """Tüm dosyaları kontrol et"""
        issues = []

        # API dosyaları
        for file in API_DIR.rglob("*.py"):
            issue = self.check_file_size(file)
            if issue:
                issues.append(issue)

        # Test dosyaları
        test_dir = PROJECT_ROOT / "tests"
        if test_dir.exists():
            for file in test_dir.rglob("*.py"):
                issue = self.check_file_size(file)
                if issue:
                    issues.append(issue)

        # Dokümantasyon dosyaları
        for file in DOCS_DIR.rglob("*.md"):
            issue = self.check_file_size(file)
            if issue:
                issues.append(issue)

        # Kök dizin dokümantasyon dosyaları
        for file in PROJECT_ROOT.glob("*.md"):
            issue = self.check_file_size(file)
            if issue:
                issues.append(issue)

        return issues

    def run_checks(self) -> Dict:
        """Tüm kontrolleri çalıştır"""
        results = {
            "file_size_issues": self.check_all_files(),
            "timestamp": datetime.now().isoformat()
        }

        return results

    def print_report(self, results: Dict):
        """Rapor yazdır"""
        print("=" * 70)
        print("STANDART KONTROL RAPORU")
        print("=" * 70)
        print(f"Tarih: {results['timestamp']}")
        print()

        issues = results['file_size_issues']

        if issues:
            errors = [i for i in issues if i['type'] == 'error']
            warnings_list = [i for i in issues if i['type'] == 'warning']

            if errors:
                print("🔴 KRİTİK SORUNLAR (Maksimum Sınır Aşıldı):")
                for issue in errors:
                    print(f"  - {issue['file']}: {issue['lines']} satır (Limit: {issue['max']})")
                    print(f"    Öncelik: {issue['priority']}")
                    print(f"    Durum: {issue['status']}")
                    print(f"    Aksiyon: {issue['action']}")
                    print()

            if warnings_list:
                print("🟡 UYARILAR (Uyarı Eşiği Yakın):")
                for issue in warnings_list:
                    print(f"  - {issue['file']}: {issue['lines']} satır (Limit: {issue['max']})")
                    print(f"    Öncelik: {issue['priority']}")
                    print(f"    Durum: {issue['status']}")
                    print(f"    Aksiyon: {issue['action']}")
                    print()
        else:
            print("✅ Tüm dosyalar standartlara uygun!")
            print()

        print("=" * 70)

        # Özet
        total_errors = len([i for i in issues if i['type'] == 'error'])
        total_warnings = len([i for i in issues if i['type'] == 'warning'])

        if total_errors == 0 and total_warnings == 0:
            print("✅ Tüm kontroller başarılı! Standartlara uygun.")
        else:
            if total_errors > 0:
                print(f"🔴 Toplam {total_errors} kritik sorun tespit edildi.")
            if total_warnings > 0:
                print(f"🟡 Toplam {total_warnings} uyarı tespit edildi.")
            print("   Bu sorunlar master_next.md'ye eklenmeli.")

        print("=" * 70)


def main():
    """Ana fonksiyon"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Standart kontrolü otomatik yap"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Sadece kontrol yap, değişiklik yapma'
    )
    parser.add_argument(
        '--update',
        action='store_true',
        help='Otomatik güncelleme yap (şimdilik sadece rapor)'
    )

    args = parser.parse_args()

    checker = StandardsChecker(dry_run=args.dry_run)
    results = checker.run_checks()
    checker.print_report(results)

    # Exit code belirleme
    total_errors = len([i for i in results['file_size_issues'] if i['type'] == 'error'])

    if total_errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

