"""
Backup Manager Script
Created: 2025-12-10 17:00:00
Last Modified: 2025-12-10 17:00:00
Version: 1.0.0
Description: Automated backup manager for database, configuration, and data files
"""

import sys
import shutil
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import gzip
import tarfile

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.logging_config import system_logger


class BackupManager:
    """
    Backup manager for Charger API project.

    Handles database, configuration, and data file backups.
    """

    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize backup manager.

        Args:
            backup_dir: Backup directory path. Defaults to backups/ in project root.
        """
        project_root = Path(__file__).parent.parent
        self.backup_dir = Path(backup_dir) if backup_dir else project_root / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Source paths
        self.data_dir = project_root / "data"
        self.config_file = project_root / ".env"
        self.project_root = project_root

    def backup_database(self, compress: bool = True) -> Optional[Path]:
        """
        Backup SQLite database.

        Args:
            compress: Whether to compress the backup. Defaults to True.

        Returns:
            Path to backup file, or None if backup failed.
        """
        db_path = self.data_dir / "sessions.db"
        if not db_path.exists():
            system_logger.warning(f"Database file not found: {db_path}")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"sessions_db_{timestamp}.db"
        if compress:
            backup_filename += ".gz"

        backup_path = self.backup_dir / backup_filename

        try:
            # SQLite backup using VACUUM INTO (SQLite 3.27+)
            # This creates a clean backup without WAL files
            conn = sqlite3.connect(str(db_path))
            backup_db_path = self.backup_dir / f"sessions_db_{timestamp}.db"
            conn.execute(f"VACUUM INTO '{backup_db_path}'")
            conn.close()

            if compress:
                # Compress the backup
                with open(backup_db_path, "rb") as f_in:
                    with gzip.open(backup_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_db_path.unlink()  # Remove uncompressed file
            else:
                backup_path = backup_db_path

            system_logger.info(f"Database backup created: {backup_path}")
            return backup_path

        except Exception as e:
            system_logger.error(f"Database backup failed: {e}", exc_info=True)
            return None

    def backup_configuration(self) -> Optional[Path]:
        """
        Backup configuration files.

        Returns:
            Path to backup file, or None if backup failed.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"config_{timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_filename

        files_to_backup = []

        # .env file
        if self.config_file.exists():
            files_to_backup.append(self.config_file)

        # station_info.json
        station_info = self.data_dir / "station_info.json"
        if station_info.exists():
            files_to_backup.append(station_info)

        if not files_to_backup:
            system_logger.warning("No configuration files found to backup")
            return None

        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                for file_path in files_to_backup:
                    tar.add(file_path, arcname=file_path.name)

            system_logger.info(f"Configuration backup created: {backup_path}")
            return backup_path

        except Exception as e:
            system_logger.error(f"Configuration backup failed: {e}", exc_info=True)
            return None

    def backup_all(self, compress: bool = True) -> Dict[str, Optional[Path]]:
        """
        Backup all data (database + configuration).

        Args:
            compress: Whether to compress backups. Defaults to True.

        Returns:
            Dictionary with backup file paths.
        """
        results = {
            "database": self.backup_database(compress=compress),
            "configuration": self.backup_configuration(),
        }

        # Create backup manifest
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "backups": {
                "database": str(results["database"]) if results["database"] else None,
                "configuration": (
                    str(results["configuration"]) if results["configuration"] else None
                ),
            },
        }

        manifest_path = (
            self.backup_dir
            / f"manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        system_logger.info(f"Backup manifest created: {manifest_path}")
        return results

    def cleanup_old_backups(self, keep_days: int = 7) -> int:
        """
        Clean up old backup files.

        Args:
            keep_days: Number of days to keep backups. Defaults to 7.

        Returns:
            Number of files deleted.
        """
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)

        for backup_file in self.backup_dir.glob("*"):
            if backup_file.is_file() and backup_file.stat().st_mtime < cutoff_time:
                try:
                    backup_file.unlink()
                    deleted_count += 1
                    system_logger.debug(f"Deleted old backup: {backup_file}")
                except Exception as e:
                    system_logger.error(f"Failed to delete backup {backup_file}: {e}")

        if deleted_count > 0:
            system_logger.info(f"Cleaned up {deleted_count} old backup files")

        return deleted_count

    def list_backups(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all backup files.

        Returns:
            Dictionary with backup file lists grouped by type.
        """
        backups = {"database": [], "configuration": [], "manifest": []}

        for backup_file in sorted(
            self.backup_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            if backup_file.name.startswith("sessions_db_"):
                backups["database"].append(
                    {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size": backup_file.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            backup_file.stat().st_mtime
                        ).isoformat(),
                    }
                )
            elif backup_file.name.startswith("config_"):
                backups["configuration"].append(
                    {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size": backup_file.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            backup_file.stat().st_mtime
                        ).isoformat(),
                    }
                )
            elif backup_file.name.startswith("manifest_"):
                backups["manifest"].append(
                    {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size": backup_file.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            backup_file.stat().st_mtime
                        ).isoformat(),
                    }
                )

        return backups


def main():
    """Main function for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Charger API Backup Manager")
    parser.add_argument(
        "--backup-dir",
        type=str,
        help="Backup directory path (default: backups/ in project root)",
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Do not compress database backups",
    )
    parser.add_argument(
        "--cleanup",
        type=int,
        metavar="DAYS",
        help="Clean up backups older than specified days",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all backup files",
    )
    parser.add_argument(
        "--database-only",
        action="store_true",
        help="Backup only database",
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Backup only configuration",
    )

    args = parser.parse_args()

    manager = BackupManager(backup_dir=args.backup_dir)

    if args.list:
        backups = manager.list_backups()
        print("\n=== Backup Files ===")
        for backup_type, files in backups.items():
            print(f"\n{backup_type.upper()}:")
            if files:
                for file_info in files:
                    size_mb = file_info["size"] / (1024 * 1024)
                    print(
                        f"  - {file_info['filename']} ({size_mb:.2f} MB) - {file_info['modified']}"
                    )
            else:
                print("  (no backups)")
        return

    if args.cleanup:
        deleted = manager.cleanup_old_backups(keep_days=args.cleanup)
        print(f"Cleaned up {deleted} old backup files")
        return

    # Perform backups
    if args.database_only:
        result = manager.backup_database(compress=not args.no_compress)
        if result:
            print(f"Database backup created: {result}")
        else:
            print("Database backup failed")
            sys.exit(1)
    elif args.config_only:
        result = manager.backup_configuration()
        if result:
            print(f"Configuration backup created: {result}")
        else:
            print("Configuration backup failed")
            sys.exit(1)
    else:
        results = manager.backup_all(compress=not args.no_compress)
        print("\n=== Backup Results ===")
        for backup_type, path in results.items():
            if path:
                print(f"{backup_type}: {path}")
            else:
                print(f"{backup_type}: FAILED")
                sys.exit(1)

    # Cleanup old backups (keep last 7 days)
    manager.cleanup_old_backups(keep_days=7)


if __name__ == "__main__":
    main()
