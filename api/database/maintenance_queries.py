"""
Maintenance Queries Module
Created: 2025-12-10 21:09:49
Last Modified: 2025-12-22 17:33:00
Version: 1.1.0
Description: Database bakım ve temizlik operasyonları mixin'i.

Notes:
  - Admin UI (HTTP Basic) için admin kullanıcı doğrulama ve OCPP station profile
    CRUD query'leri eklendi.
  - Admin parolası DB'de PBKDF2-SHA256 ile hash+salt olarak saklanır.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional

from api.logging_config import system_logger


class MaintenanceQueryMixin:
    """Database bakım operasyonlarını sağlayan mixin."""

    _ADMIN_DEFAULT_USERNAME = "admin"
    _ADMIN_DEFAULT_PASSWORD = "admin123"
    _ADMIN_PBKDF2_ITERATIONS = 150_000

    _PROFILE_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

    @staticmethod
    def _pbkdf2_sha256(password: str, salt: bytes, iterations: int) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
            dklen=32,
        )

    def ensure_default_admin_user(self) -> None:
        """
        Varsayılan admin kullanıcıyı (admin/admin123) bir kereye mahsus oluştur.

        Not:
          - Bu fonksiyon secret üretmez; sadece ilk kurulumda default credential yazar.
          - UI üzerinden şifre değiştirilebilir.
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                self._ensure_admin_tables(cursor)
                cursor.execute(
                    "SELECT username FROM admin_users WHERE username=?",
                    (self._ADMIN_DEFAULT_USERNAME,),
                )
                if cursor.fetchone():
                    return

                now = int(time.time())
                salt = os.urandom(16)
                iterations = int(self._ADMIN_PBKDF2_ITERATIONS)
                pw_hash = self._pbkdf2_sha256(
                    self._ADMIN_DEFAULT_PASSWORD, salt, iterations
                )
                cursor.execute(
                    """
                    INSERT INTO admin_users
                    (username, password_salt, password_hash, password_iterations, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._ADMIN_DEFAULT_USERNAME,
                        salt,
                        pw_hash,
                        iterations,
                        now,
                        now,
                    ),
                )
                conn.commit()
                system_logger.warning(
                    "Default admin user created (please change password via /admin)"
                )
            except sqlite3.OperationalError as exc:
                # If app was started before schema update, create tables on demand.
                if "no such table" in str(exc).lower():
                    try:
                        cursor = conn.cursor()
                        self._ensure_admin_tables(cursor)
                        conn.commit()
                        return self.ensure_default_admin_user()
                    except Exception as inner:
                        conn.rollback()
                        system_logger.error(
                            f"ensure_default_admin_user recovery failed: {inner}",
                            exc_info=True,
                        )
                        raise
                conn.rollback()
                system_logger.error(
                    f"ensure_default_admin_user error: {exc}", exc_info=True
                )
                raise
            except Exception as exc:
                conn.rollback()
                system_logger.error(
                    f"ensure_default_admin_user error: {exc}", exc_info=True
                )
                raise

    def verify_admin_basic_auth(self, username: str, password: str) -> bool:
        """Admin HTTP Basic kimlik bilgilerini DB'deki hash ile doğrula."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                self._ensure_admin_tables(cursor)
                cursor.execute(
                    """
                    SELECT password_salt, password_hash, password_iterations
                    FROM admin_users
                    WHERE username=?
                    """,
                    (username,),
                )
                row = cursor.fetchone()
                if not row:
                    return False

                salt = row["password_salt"]
                pw_hash = row["password_hash"]
                iterations = int(row["password_iterations"])
                candidate = self._pbkdf2_sha256(password, salt, iterations)
                return hmac.compare_digest(candidate, pw_hash)
            except Exception as exc:
                system_logger.error(
                    f"verify_admin_basic_auth error: {exc}", exc_info=True
                )
                return False

    def set_admin_password(self, username: str, new_password: str) -> None:
        """Admin parolasını güncelle (hash+salt)."""
        if not new_password or len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters")

        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                self._ensure_admin_tables(cursor)
                now = int(time.time())
                salt = os.urandom(16)
                iterations = int(self._ADMIN_PBKDF2_ITERATIONS)
                pw_hash = self._pbkdf2_sha256(new_password, salt, iterations)
                cursor.execute(
                    """
                    UPDATE admin_users
                    SET password_salt=?, password_hash=?, password_iterations=?, updated_at=?
                    WHERE username=?
                    """,
                    (salt, pw_hash, iterations, now, username),
                )
                if cursor.rowcount == 0:
                    # Create if missing (defensive)
                    cursor.execute(
                        """
                        INSERT INTO admin_users
                        (username, password_salt, password_hash, password_iterations, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (username, salt, pw_hash, iterations, now, now),
                    )
                conn.commit()
            except Exception as exc:
                conn.rollback()
                system_logger.error(f"set_admin_password error: {exc}", exc_info=True)
                raise

    @classmethod
    def validate_profile_key(cls, profile_key: str) -> str:
        key = (profile_key or "").strip()
        if not cls._PROFILE_KEY_RE.match(key):
            raise ValueError(
                "Invalid profile_key. Allowed: A-Z a-z 0-9 _ . - (1-64 chars)"
            )
        return key

    @staticmethod
    def _ensure_admin_tables(cursor: sqlite3.Cursor) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                username TEXT PRIMARY KEY,
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                password_iterations INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ocpp_station_profiles (
                profile_key TEXT PRIMARY KEY,
                station_name TEXT NOT NULL,
                ocpp_version TEXT NOT NULL CHECK(ocpp_version IN ('2.0.1', '1.6j')),
                ocpp201_url TEXT,
                ocpp16_url TEXT,
                vendor_name TEXT NOT NULL,
                model TEXT NOT NULL,
                serial_number TEXT,
                firmware_version TEXT,
                password_env_var TEXT NOT NULL,
                heartbeat_seconds INTEGER NOT NULL DEFAULT 60 CHECK(heartbeat_seconds > 0),
                enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ocpp_station_profiles_enabled
            ON ocpp_station_profiles(enabled)
            """
        )

    def list_ocpp_profiles(self) -> List[Dict[str, Any]]:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            self._ensure_admin_tables(cursor)
            cursor.execute(
                """
                SELECT
                  profile_key, station_name, ocpp_version, ocpp201_url, ocpp16_url,
                  vendor_name, model, serial_number, firmware_version, password_env_var,
                  heartbeat_seconds, enabled, created_at, updated_at
                FROM ocpp_station_profiles
                ORDER BY updated_at DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_ocpp_profile(self, profile_key: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            self._ensure_admin_tables(cursor)
            cursor.execute(
                """
                SELECT
                  profile_key, station_name, ocpp_version, ocpp201_url, ocpp16_url,
                  vendor_name, model, serial_number, firmware_version, password_env_var,
                  heartbeat_seconds, enabled, created_at, updated_at
                FROM ocpp_station_profiles
                WHERE profile_key=?
                """,
                (profile_key,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def upsert_ocpp_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        profile_key = self.validate_profile_key(profile.get("profile_key", ""))
        station_name = (profile.get("station_name") or "").strip()
        ocpp_version = (profile.get("ocpp_version") or "").strip()
        ocpp201_url = (profile.get("ocpp201_url") or "").strip() or None
        ocpp16_url = (profile.get("ocpp16_url") or "").strip() or None
        vendor_name = (profile.get("vendor_name") or "").strip()
        model = (profile.get("model") or "").strip()
        serial_number = (profile.get("serial_number") or "").strip() or None
        firmware_version = (profile.get("firmware_version") or "").strip() or None
        password_env_var = (profile.get("password_env_var") or "").strip()

        heartbeat_seconds_raw = profile.get("heartbeat_seconds")
        heartbeat_seconds = int(heartbeat_seconds_raw or 60)
        enabled = 1 if bool(profile.get("enabled", True)) else 0

        if not station_name:
            raise ValueError("station_name is required")
        if ocpp_version not in ("2.0.1", "1.6j"):
            raise ValueError("ocpp_version must be '2.0.1' or '1.6j'")
        expected_suffix = f"/{station_name}"

        def _validate_url_field(field: str, url: str) -> None:
            if not str(url).startswith(("ws://", "wss://")):
                raise ValueError(f"{field} must start with ws:// or wss://")
            if not str(url).rstrip("/").endswith(expected_suffix):
                raise ValueError(f"{field} must end with '{expected_suffix}'")

        # NOTE: Single-protocol station behavior (fallback disabled by default).
        # - For 2.0.1 profiles, only ocpp201_url is required.
        # - For 1.6j profiles, only ocpp16_url is required.
        if ocpp_version == "2.0.1":
            if not ocpp201_url:
                raise ValueError("ocpp201_url is required for ocpp_version=2.0.1")
            _validate_url_field("ocpp201_url", ocpp201_url)
            if ocpp16_url:
                _validate_url_field("ocpp16_url", ocpp16_url)
        else:  # 1.6j
            if not ocpp16_url:
                raise ValueError("ocpp16_url is required for ocpp_version=1.6j")
            _validate_url_field("ocpp16_url", ocpp16_url)
            if ocpp201_url:
                _validate_url_field("ocpp201_url", ocpp201_url)
        if not vendor_name:
            raise ValueError("vendor_name is required")
        if not model:
            raise ValueError("model is required")
        if not password_env_var:
            raise ValueError("password_env_var is required (must exist in .env)")
        if heartbeat_seconds <= 0 or heartbeat_seconds > 3600:
            raise ValueError("heartbeat_seconds must be between 1 and 3600")

        now = int(time.time())
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                self._ensure_admin_tables(cursor)
                existing = self.get_ocpp_profile(profile_key)
                if existing:
                    cursor.execute(
                        """
                        UPDATE ocpp_station_profiles
                        SET station_name=?, ocpp_version=?, ocpp201_url=?, ocpp16_url=?,
                            vendor_name=?, model=?, serial_number=?, firmware_version=?,
                            password_env_var=?, heartbeat_seconds=?, enabled=?, updated_at=?
                        WHERE profile_key=?
                        """,
                        (
                            station_name,
                            ocpp_version,
                            ocpp201_url,
                            ocpp16_url,
                            vendor_name,
                            model,
                            serial_number,
                            firmware_version,
                            password_env_var,
                            heartbeat_seconds,
                            enabled,
                            now,
                            profile_key,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO ocpp_station_profiles
                        (profile_key, station_name, ocpp_version, ocpp201_url, ocpp16_url,
                         vendor_name, model, serial_number, firmware_version,
                         password_env_var, heartbeat_seconds, enabled, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            profile_key,
                            station_name,
                            ocpp_version,
                            ocpp201_url,
                            ocpp16_url,
                            vendor_name,
                            model,
                            serial_number,
                            firmware_version,
                            password_env_var,
                            heartbeat_seconds,
                            enabled,
                            now,
                            now,
                        ),
                    )
                conn.commit()
                return self.get_ocpp_profile(profile_key) or {}
            except Exception as exc:
                conn.rollback()
                system_logger.error(f"upsert_ocpp_profile error: {exc}", exc_info=True)
                raise

    def delete_ocpp_profile(self, profile_key: str) -> bool:
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                self._ensure_admin_tables(cursor)
                cursor.execute(
                    "DELETE FROM ocpp_station_profiles WHERE profile_key=?",
                    (profile_key,),
                )
                conn.commit()
                return cursor.rowcount > 0
            except Exception as exc:
                conn.rollback()
                system_logger.error(f"delete_ocpp_profile error: {exc}", exc_info=True)
                raise

    def cleanup_old_sessions(self, max_sessions: int = 1000) -> int:
        """
        Eski session kayıtlarını temizler.

        Returns:
            Silinen session sayısı.
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM sessions")
                total_count = cursor.fetchone()[0]

                if total_count <= max_sessions:
                    return 0

                to_remove = int(total_count * 0.1)

                cursor.execute(
                    """
                    DELETE FROM sessions
                    WHERE session_id IN (
                        SELECT session_id FROM sessions
                        ORDER BY start_time ASC
                        LIMIT ?
                    )
                    """,
                    (to_remove,),
                )

                conn.commit()
                deleted_count = cursor.rowcount
                system_logger.info(
                    f"Cleaned up {deleted_count} old sessions (total: {total_count})"
                )
                return deleted_count
            except Exception as exc:
                system_logger.error(f"Cleanup old sessions error: {exc}", exc_info=True)
                conn.rollback()
                return 0
