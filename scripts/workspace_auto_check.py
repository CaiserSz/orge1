#!/usr/bin/env python3
"""
Workspace Otomatik Kontrol Script'i

Bu script workspace standartlarını kontrol eder:
1. Dosya sayısı standartları (kök dizin .md dosyaları < 30)
2. Klasör sayısı standartları (< 15 ideal, < 20 uyarı)
3. Dosya organizasyonu (kök dizinde gereksiz dosyalar)
4. Standartlara uygunluk kontrolü
5. Gereksiz dosyaların tespiti (cache, temp, backup)

Kullanım:
    python3 scripts/workspace_auto_check.py [--dry-run] [--fix]
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Proje kök dizini
PROJECT_ROOT = Path(__file__).parent.parent

# Standartlar
MAX_MD_FILES_ROOT = 30
WARNING_MD_FILES_ROOT = 25
MAX_DIRECTORIES = 20
WARNING_DIRECTORIES = 15
MAX_TOTAL_SIZE_MB = 100
WARNING_TOTAL_SIZE_MB = 80


class WorkspaceChecker:
    """Workspace standartlarını kontrol eden sınıf"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.issues = []
        self.warnings = []

    def check_root_md_files(self) -> Dict:
        """Kök dizindeki .md dosyalarını kontrol et"""
        root_md_files = list(PROJECT_ROOT.glob("*.md"))
        count = len(root_md_files)

        issue = None
        if count > MAX_MD_FILES_ROOT:
            issue = {
                "type": "error",
                "message": f"Kök dizinde çok fazla .md dosyası: {count} (Limit: {MAX_MD_FILES_ROOT})",
                "files": [f.name for f in root_md_files],
                "action": "Analiz/audit raporları reports/ klasörüne, standartlar docs/standards/ klasörüne taşınmalı"
            }
        elif count > WARNING_MD_FILES_ROOT:
            issue = {
                "type": "warning",
                "message": f"Kök dizinde .md dosyası sayısı uyarı eşiğinde: {count} (İdeal: < {WARNING_MD_FILES_ROOT})",
                "files": [f.name for f in root_md_files],
                "action": "Yakında reorganizasyon gerekebilir"
            }

        return {
            "count": count,
            "max": MAX_MD_FILES_ROOT,
            "warning": WARNING_MD_FILES_ROOT,
            "issue": issue
        }

    def check_directory_count(self) -> Dict:
        """Klasör sayısını kontrol et"""
        directories = [d for d in PROJECT_ROOT.iterdir() if d.is_dir() and not d.name.startswith('.')]
        count = len(directories)

        issue = None
        if count > MAX_DIRECTORIES:
            issue = {
                "type": "error",
                "message": f"Çok fazla klasör: {count} (Limit: {MAX_DIRECTORIES})",
                "directories": [d.name for d in directories],
                "action": "Klasör birleştirme veya arşivleme gerekebilir"
            }
        elif count > WARNING_DIRECTORIES:
            issue = {
                "type": "warning",
                "message": f"Klasör sayısı uyarı eşiğinde: {count} (İdeal: < {WARNING_DIRECTORIES})",
                "directories": [d.name for d in directories],
                "action": "Yakında reorganizasyon gerekebilir"
            }

        return {
            "count": count,
            "max": MAX_DIRECTORIES,
            "warning": WARNING_DIRECTORIES,
            "issue": issue
        }

    def check_unnecessary_files(self) -> List[Dict]:
        """Gereksiz dosyaları tespit et"""
        unnecessary = []

        # Geçici dosyalar
        temp_patterns = ['*.tmp', '*.temp', '*.bak', '*.old', '*.backup']
        for pattern in temp_patterns:
            for file in PROJECT_ROOT.rglob(pattern):
                if file.is_file():
                    unnecessary.append({
                        "file": str(file.relative_to(PROJECT_ROOT)),
                        "type": "temp",
                        "action": "Silinmeli"
                    })

        # Yedek dosyalar
        backup_patterns = ['*_backup.*', '*_old.*', '*.backup']
        for pattern in backup_patterns:
            for file in PROJECT_ROOT.rglob(pattern):
                if file.is_file() and file not in [f for f in PROJECT_ROOT.rglob('*.backup')]:
                    unnecessary.append({
                        "file": str(file.relative_to(PROJECT_ROOT)),
                        "type": "backup",
                        "action": "Git'te varsa silinmeli"
                    })

        return unnecessary

    def check_file_organization(self) -> List[Dict]:
        """Dosya organizasyonunu kontrol et"""
        issues = []

        # Kök dizindeki analiz/audit raporları
        root_files = list(PROJECT_ROOT.glob("*.md"))
        analysis_patterns = ['*ANALYSIS*.md', '*AUDIT*.md', '*REPORT*.md', '*REVIEW*.md']

        for file in root_files:
            for pattern in analysis_patterns:
                if file.match(pattern):
                    issues.append({
                        "file": file.name,
                        "type": "organization",
                        "message": f"Analiz/audit raporu kök dizinde: {file.name}",
                        "action": f"reports/ klasörüne taşınmalı"
                    })
                    break

        # Standart dokümantasyon kontrolü
        standards_patterns = ['*STANDARDS*.md', '*STANDARD*.md']
        for file in root_files:
            for pattern in standards_patterns:
                if file.match(pattern):
                    issues.append({
                        "file": file.name,
                        "type": "organization",
                        "message": f"Standart dokümantasyon kök dizinde: {file.name}",
                        "action": f"docs/standards/ klasörüne taşınmalı"
                    })
                    break

        return issues

    def check_workspace_size(self) -> Dict:
        """Workspace boyutunu kontrol et"""
        total_size = 0
        for file in PROJECT_ROOT.rglob('*'):
            if file.is_file():
                try:
                    total_size += file.stat().st_size
                except:
                    pass

        total_size_mb = total_size / (1024 * 1024)

        issue = None
        if total_size_mb > MAX_TOTAL_SIZE_MB:
            issue = {
                "type": "error",
                "message": f"Workspace boyutu çok büyük: {total_size_mb:.2f} MB (Limit: {MAX_TOTAL_SIZE_MB} MB)",
                "action": "Temizlik ve arşivleme gerekebilir"
            }
        elif total_size_mb > WARNING_TOTAL_SIZE_MB:
            issue = {
                "type": "warning",
                "message": f"Workspace boyutu uyarı eşiğinde: {total_size_mb:.2f} MB (İdeal: < {WARNING_TOTAL_SIZE_MB} MB)",
                "action": "Yakında temizlik gerekebilir"
            }

        return {
            "size_mb": total_size_mb,
            "max": MAX_TOTAL_SIZE_MB,
            "warning": WARNING_TOTAL_SIZE_MB,
            "issue": issue
        }

    def run_checks(self) -> Dict:
        """Tüm kontrolleri çalıştır"""
        results = {
            "root_md_files": self.check_root_md_files(),
            "directory_count": self.check_directory_count(),
            "unnecessary_files": self.check_unnecessary_files(),
            "file_organization": self.check_file_organization(),
            "workspace_size": self.check_workspace_size(),
            "timestamp": datetime.now().isoformat()
        }

        return results

    def print_report(self, results: Dict):
        """Rapor yazdır"""
        print("=" * 70)
        print("WORKSPACE OTOMATIK KONTROL RAPORU")
        print("=" * 70)
        print(f"Tarih: {results['timestamp']}")
        print()

        # Kök dizin .md dosyaları
        md_result = results['root_md_files']
        print(f"📄 Kök Dizin .md Dosyaları: {md_result['count']} (İdeal: < {md_result['warning']}, Limit: {md_result['max']})")
        if md_result['issue']:
            if md_result['issue']['type'] == 'error':
                print(f"  🔴 {md_result['issue']['message']}")
            else:
                print(f"  🟡 {md_result['issue']['message']}")
            print(f"  Aksiyon: {md_result['issue']['action']}")
            if 'files' in md_result['issue']:
                print(f"  Dosyalar: {', '.join(md_result['issue']['files'][:5])}...")
        else:
            print("  ✅ Standartlara uygun")
        print()

        # Klasör sayısı
        dir_result = results['directory_count']
        print(f"📁 Klasör Sayısı: {dir_result['count']} (İdeal: < {dir_result['warning']}, Limit: {dir_result['max']})")
        if dir_result['issue']:
            if dir_result['issue']['type'] == 'error':
                print(f"  🔴 {dir_result['issue']['message']}")
            else:
                print(f"  🟡 {dir_result['issue']['message']}")
            print(f"  Aksiyon: {dir_result['issue']['action']}")
        else:
            print("  ✅ Standartlara uygun")
        print()

        # Workspace boyutu
        size_result = results['workspace_size']
        print(f"💾 Workspace Boyutu: {size_result['size_mb']:.2f} MB (İdeal: < {size_result['warning']} MB, Limit: {size_result['max']} MB)")
        if size_result['issue']:
            if size_result['issue']['type'] == 'error':
                print(f"  🔴 {size_result['issue']['message']}")
            else:
                print(f"  🟡 {size_result['issue']['message']}")
            print(f"  Aksiyon: {size_result['issue']['action']}")
        else:
            print("  ✅ Standartlara uygun")
        print()

        # Gereksiz dosyalar
        unnecessary = results['unnecessary_files']
        if unnecessary:
            print(f"🗑️  Gereksiz Dosyalar: {len(unnecessary)} adet")
            for item in unnecessary[:10]:  # İlk 10'unu göster
                print(f"  - {item['file']} ({item['type']}) → {item['action']}")
            if len(unnecessary) > 10:
                print(f"  ... ve {len(unnecessary) - 10} dosya daha")
        else:
            print("✅ Gereksiz dosya yok")
        print()

        # Dosya organizasyonu
        org_issues = results['file_organization']
        if org_issues:
            print(f"📋 Dosya Organizasyonu Sorunları: {len(org_issues)} adet")
            for issue in org_issues[:10]:  # İlk 10'unu göster
                print(f"  - {issue['file']}: {issue['message']}")
                print(f"    Aksiyon: {issue['action']}")
            if len(org_issues) > 10:
                print(f"  ... ve {len(org_issues) - 10} sorun daha")
        else:
            print("✅ Dosya organizasyonu standartlara uygun")
        print()

        print("=" * 70)

        # Özet
        total_issues = (
            (1 if md_result['issue'] and md_result['issue']['type'] == 'error' else 0) +
            (1 if dir_result['issue'] and dir_result['issue']['type'] == 'error' else 0) +
            (1 if size_result['issue'] and size_result['issue']['type'] == 'error' else 0) +
            len(unnecessary) +
            len(org_issues)
        )

        total_warnings = (
            (1 if md_result['issue'] and md_result['issue']['type'] == 'warning' else 0) +
            (1 if dir_result['issue'] and dir_result['issue']['type'] == 'warning' else 0) +
            (1 if size_result['issue'] and size_result['issue']['type'] == 'warning' else 0)
        )

        if total_issues == 0 and total_warnings == 0:
            print("✅ Tüm kontroller başarılı! Workspace standartlara uygun.")
        else:
            if total_issues > 0:
                print(f"🔴 Toplam {total_issues} kritik sorun tespit edildi.")
            if total_warnings > 0:
                print(f"🟡 Toplam {total_warnings} uyarı tespit edildi.")
            print("   Detaylı bilgi için yukarıdaki rapora bakınız.")

        print("=" * 70)


def main():
    """Ana fonksiyon"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Workspace standartlarını otomatik kontrol"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Sadece kontrol yap, değişiklik yapma'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Otomatik düzeltme yap (şimdilik sadece rapor)'
    )

    args = parser.parse_args()

    checker = WorkspaceChecker(dry_run=args.dry_run)
    results = checker.run_checks()
    checker.print_report(results)

    # Exit code belirleme
    total_errors = (
        (1 if results['root_md_files']['issue'] and results['root_md_files']['issue']['type'] == 'error' else 0) +
        (1 if results['directory_count']['issue'] and results['directory_count']['issue']['type'] == 'error' else 0) +
        (1 if results['workspace_size']['issue'] and results['workspace_size']['issue']['type'] == 'error' else 0) +
        len(results['unnecessary_files']) +
        len(results['file_organization'])
    )

    if total_errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

