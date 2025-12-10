"""
Charge Service
Created: 2025-12-10 15:30:00
Last Modified: 2025-12-10
Version: 1.1.0
Description: Charge control business logic service layer
"""

from datetime import datetime
from typing import Dict, Any, Optional
import hashlib

from api.logging_config import system_logger
from api.models import ChargeStartRequest, ChargeStopRequest
from api.cache import CacheInvalidator
from api.services.base_service import BaseService
from api.state_validation import (
    validate_state,
    check_state_for_charge_start,
    check_state_changed,
)


class ChargeService(BaseService):
    """
    Charge control business logic service

    Charge start/stop işlemlerinin business logic'ini içerir.
    Router'lar sadece HTTP handling yapar, business logic burada.
    """

    def start_charge(
        self,
        request_body: ChargeStartRequest,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Şarj başlatma business logic

        Args:
            request_body: Charge start request body
            user_id: User ID (audit trail için, None ise config'den alınır)
            api_key: API key (audit trail için)

        Returns:
            Success response dict

        Raises:
            ValueError: Business logic hataları için
        """
        # Bridge bağlantısını kontrol et
        self._ensure_connected()

        # User ID'yi al (request body'den gelen user_id öncelikli, yoksa config'den)
        if not user_id:
            user_id = self._get_user_id(None)

        # Kritik işlemleri logla (şarj başlatma)
        if user_id:
            self._log_event(
                event_type="charge_start",
                event_data={
                    "user_id": user_id,
                    "api_key_hash": (
                        hashlib.sha256(api_key.encode()).hexdigest()[:16]
                        if api_key
                        else None
                    ),
                    "timestamp": datetime.now().isoformat(),
                },
            )
            # Session manager'a user_id bilgisini geçir (CHARGE_STARTED event'i için)
            try:
                from api.session import get_session_manager

                session_manager = get_session_manager()
                if session_manager:
                    # pending_user_id'ye user_id'yi kaydet
                    with session_manager.pending_user_id_lock:
                        session_manager.pending_user_id = user_id
            except Exception:
                # Session manager yoksa veya hata varsa devam et
                pass

        # Mevcut durumu kontrol et ve state validate et
        current_status = self.bridge.get_status()
        state, state_name = validate_state(
            current_status,
            endpoint="/api/charge/start",
            user_id=user_id,
            allow_none=False,
        )

        # Charge start için state kontrolü
        check_state_for_charge_start(state, state_name, "/api/charge/start", user_id)

        # Komut gönderilmeden önce son bir kez STATE kontrolü yapalım (race condition önlemi)
        final_status_check = self.bridge.get_status()
        if final_status_check:
            final_state = final_status_check.get("STATE")
            check_state_changed(state, final_state, "/api/charge/start", user_id)

        success = self.bridge.send_authorization()

        if not success:
            error_msg = "Şarj başlatma komutu gönderilemedi"
            system_logger.error(
                f"Charge start failed: {error_msg}",
                extra={
                    "endpoint": "/api/charge/start",
                    "user_id": user_id,
                    "current_state": state,
                    "error_type": "COMMAND_SEND_ERROR",
                },
            )
            raise ValueError(error_msg)

        # Status ve session cache'lerini invalidate et (state değişti)
        CacheInvalidator.invalidate_status()
        CacheInvalidator.invalidate_session()

        return {
            "success": True,
            "message": "Şarj başlatma komutu gönderildi",
            "data": {"command": "authorization"},
        }

    def stop_charge(
        self,
        request_body: ChargeStopRequest,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Şarj durdurma business logic

        Args:
            request_body: Charge stop request body
            user_id: User ID (audit trail için, None ise config'den alınır)
            api_key: API key (audit trail için)

        Returns:
            Success response dict

        Raises:
            ValueError: Business logic hataları için
        """
        # Bridge bağlantısını kontrol et
        self._ensure_connected()

        # User ID'yi al (request body'den gelen user_id öncelikli, yoksa config'den)
        if not user_id:
            user_id = self._get_user_id(None)

        # Kritik işlemleri logla (şarj durdurma)
        if user_id:
            self._log_event(
                event_type="charge_stop",
                event_data={
                    "user_id": user_id,
                    "api_key_hash": (
                        hashlib.sha256(api_key.encode()).hexdigest()[:16]
                        if api_key
                        else None
                    ),
                    "timestamp": datetime.now().isoformat(),
                },
            )

        # Charge stop komutu gönder
        success = self.bridge.send_charge_stop()

        if not success:
            error_msg = "Şarj durdurma komutu gönderilemedi"
            system_logger.error(
                f"Charge stop failed: {error_msg}",
                extra={
                    "endpoint": "/api/charge/stop",
                    "user_id": user_id,
                    "error_type": "COMMAND_SEND_ERROR",
                },
            )
            raise ValueError(error_msg)

        # Status ve session cache'lerini invalidate et (state değişti)
        CacheInvalidator.invalidate_status()
        CacheInvalidator.invalidate_session()

        return {
            "success": True,
            "message": "Şarj durdurma komutu gönderildi",
            "data": {"command": "charge_stop"},
        }
