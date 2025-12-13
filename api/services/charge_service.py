"""
Charge Service
Created: 2025-12-10 15:30:00
Last Modified: 2025-12-13 21:45:00
Version: 1.2.0
Description: Charge control business logic service layer
"""

import hashlib
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

from api.cache import CacheInvalidator
from api.logging_config import system_logger
from api.models import ChargeStartRequest, ChargeStopRequest
from api.services.base_service import BaseService
from api.state_validation import (
    check_state_changed,
    check_state_for_charge_start,
    validate_state,
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

        # Şarj sonrasında MAX akımı standart değere (varsayılan: 32A veya station_info.max_current_amp)
        # otomatik geri al. Şarj esnasında current set yasak olduğu için, state düşene kadar bekler.
        try:
            from api.station_info import get_station_info

            station_info = get_station_info() or {}
            reset_amp_raw = station_info.get("max_current_amp") or 32
            reset_amp = int(reset_amp_raw)
            reset_amp = max(6, min(32, reset_amp))

            def _reset_current_after_stop():
                try:
                    from api.event_detector import ESP32State
                    from api.models import CurrentSetRequest
                    from api.services.current_service import CurrentService

                    current_service = CurrentService(self.bridge)
                    for _ in range(20):  # ~20 saniye dene
                        status = None
                        try:
                            status = self.bridge.get_status()
                        except Exception:
                            status = None

                        state = (
                            status.get("STATE") if isinstance(status, dict) else None
                        )
                        # IDLE/EV_CONNECTED/READY gibi state'lerde current set yapılabilir
                        if state is None or state < ESP32State.CHARGING.value:
                            try:
                                current_service.set_current(
                                    CurrentSetRequest(amperage=reset_amp),
                                    user_id=user_id,
                                    api_key=api_key,
                                )
                                system_logger.info(
                                    "Auto max current reset after stop",
                                    extra={
                                        "reset_amp": reset_amp,
                                        "user_id": user_id,
                                        "endpoint": "/api/charge/stop",
                                    },
                                )
                            except Exception as exc:
                                system_logger.warning(
                                    f"Auto current reset failed: {exc}",
                                    extra={"reset_amp": reset_amp, "user_id": user_id},
                                )
                            break
                        time.sleep(1)
                except Exception as exc:
                    system_logger.warning(f"Auto current reset worker failed: {exc}")

            threading.Thread(
                target=_reset_current_after_stop,
                daemon=True,
                name="auto_current_reset",
            ).start()
        except Exception:
            # Non-critical; stop işlemi başarılı olsa bile reset opsiyonel
            pass

        # Status ve session cache'lerini invalidate et (state değişti)
        CacheInvalidator.invalidate_status()
        CacheInvalidator.invalidate_session()

        return {
            "success": True,
            "message": "Şarj durdurma komutu gönderildi",
            "data": {"command": "charge_stop"},
        }
