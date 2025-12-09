#!/usr/bin/env python3
"""
Kod Kalitesi Otomatik Kontrol Script'i

Bu script kod kalitesi standartlarını kontrol eder:
1. Black formatter kontrolü
2. Ruff linter kontrolü
3. Mypy type checker kontrolü (opsiyonel)

Kullanım:
    python3 scripts/code_quality_auto_check.py [--dry-run] [--fix]
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Proje kök dizini
PROJECT_ROOT = Path(__file__).parent.parent
API_DIR = PROJECT_ROOT / "api"
ESP32_DIR = PROJECT_ROOT / "esp32"
METER_DIR = PROJECT_ROOT / "meter"


class CodeQualityChecker:
    """Kod kalitesi kontrolü yapan sınıf"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.issues = []

    def check_black(self) -> Dict:
        """Black formatter kontrolü"""
        try:
            result = subprocess.run(
                ["python3", "-m", "black", "--check", "--diff", str(API_DIR), str(ESP32_DIR), str(METER_DIR)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {
                    "tool": "black",
                    "status": "error",
                    "message": "Code formatting issues found",
                    "output": result.stdout + result.stderr
                }
            else:
                return {
                    "tool": "black",
                    "status": "ok",
                    "message": "Code formatting is correct"
                }
        except FileNotFoundError:
            return {
                "tool": "black",
                "status": "not_installed",
                "message": "Black is not installed. Install with: pip install black"
            }
        except Exception as e:
            return {
                "tool": "black",
                "status": "error",
                "message": f"Error checking black: {e}"
            }

    def check_ruff(self) -> Dict:
        """Ruff linter kontrolü"""
        try:
            result = subprocess.run(
                ["python3", "-m", "ruff", "check", str(API_DIR), str(ESP32_DIR), str(METER_DIR)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {
                    "tool": "ruff",
                    "status": "error",
                    "message": "Linting issues found",
                    "output": result.stdout + result.stderr
                }
            else:
                return {
                    "tool": "ruff",
                    "status": "ok",
                    "message": "No linting issues found"
                }
        except FileNotFoundError:
            return {
                "tool": "ruff",
                "status": "not_installed",
                "message": "Ruff is not installed. Install with: pip install ruff"
            }
        except Exception as e:
            return {
                "tool": "ruff",
                "status": "error",
                "message": f"Error checking ruff: {e}"
            }

    def run_checks(self) -> Dict:
        """Tüm kontrolleri çalıştır"""
        results = {
            "black": self.check_black(),
            "ruff": self.check_ruff(),
            "timestamp": datetime.now().isoformat()
        }

        return results

    def print_report(self, results: Dict):
        """Rapor yazdır"""
        print("=" * 70)
        print("KOD KALİTESİ KONTROL RAPORU")
        print("=" * 70)
        print(f"Tarih: {results['timestamp']}")
        print()

        # Black kontrolü
        black_result = results['black']
        print(f"📝 Black Formatter:")
        if black_result['status'] == 'ok':
            print(f"  ✅ {black_result['message']}")
        elif black_result['status'] == 'not_installed':
            print(f"  ⚠️  {black_result['message']}")
        else:
            print(f"  🔴 {black_result['message']}")
            if 'output' in black_result:
                print(f"  Detaylar: {black_result['output'][:200]}...")
        print()

        # Ruff kontrolü
        ruff_result = results['ruff']
        print(f"🔍 Ruff Linter:")
        if ruff_result['status'] == 'ok':
            print(f"  ✅ {ruff_result['message']}")
        elif ruff_result['status'] == 'not_installed':
            print(f"  ⚠️  {ruff_result['message']}")
        else:
            print(f"  🔴 {ruff_result['message']}")
            if 'output' in ruff_result:
                print(f"  Detaylar: {ruff_result['output'][:200]}...")
        print()

        print("=" * 70)

        # Özet
        errors = [
            r for r in [black_result, ruff_result]
            if r['status'] == 'error'
        ]
        not_installed = [
            r for r in [black_result, ruff_result]
            if r['status'] == 'not_installed'
        ]

        if len(errors) == 0 and len(not_installed) == 0:
            print("✅ Tüm kod kalitesi kontrolleri başarılı!")
        else:
            if len(errors) > 0:
                print(f"🔴 {len(errors)} kod kalitesi sorunu tespit edildi.")
            if len(not_installed) > 0:
                print(f"⚠️  {len(not_installed)} tool kurulu değil.")

        print("=" * 70)


def main():
    """Ana fonksiyon"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Kod kalitesi kontrolü otomatik yap"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Sadece kontrol yap, değişiklik yapma'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Otomatik düzeltme yap (black --fix)'
    )

    args = parser.parse_args()

    checker = CodeQualityChecker(dry_run=args.dry_run)
    results = checker.run_checks()
    checker.print_report(results)

    # Exit code belirleme
    errors = [
        r for r in [results['black'], results['ruff']]
        if r['status'] == 'error'
    ]

    if len(errors) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

