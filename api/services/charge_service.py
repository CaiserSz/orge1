"""
Charge Service
Created: 2025-12-10 15:30:00
Last Modified: 2025-12-10 15:30:00
Version: 1.0.0
Description: Charge control business logic service layer
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from api.event_detector import ESP32State
from api.logging_config import log_event, system_logger
from api.models import ChargeStartRequest, ChargeStopRequest
from api.cache import invalidate_cache
from esp32.bridge import ESP32Bridge


class ChargeService:
    """
    Charge control business logic service

    Charge start/stop işlemlerinin business logic'ini içerir.
    Router'lar sadece HTTP handling yapar, business logic burada.
    """

    def __init__(self, bridge: ESP32Bridge):
        """
        ChargeService başlatıcı

        Args:
            bridge: ESP32Bridge instance
        """
        self.bridge = bridge

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
            user_id: User ID (audit trail için)
            api_key: API key (audit trail için)

        Returns:
            Success response dict

        Raises:
            HTTPException: Business logic hataları için
        """
        # User ID'yi al (audit trail için)
        if not user_id:
            from api.config import config
            user_id = config.get_user_id()

        # Kritik işlemleri logla (şarj başlatma)
        if user_id:
            log_event(
                event_type="charge_start",
                event_data={
                    "user_id": user_id,
                    "api_key": api_key[:10] + "..." if api_key else None,
                    "timestamp": datetime.now().isoformat(),
                },
                level=logging.INFO,
            )

        if not self.bridge or not self.bridge.is_connected:
            raise ValueError("ESP32 bağlantısı yok")

        # Mevcut durumu kontrol et
        current_status = self.bridge.get_status()
        if not current_status:
            error_msg = "ESP32 durum bilgisi alınamadı"
            system_logger.error(
                f"Charge start failed: {error_msg}",
                extra={
                    "endpoint": "/api/charge/start",
                    "user_id": user_id,
                    "error_type": "ESP32_STATUS_ERROR",
                },
            )
            raise ValueError(error_msg)

        # STATE değerini al ve None kontrolü yap
        state = current_status.get("STATE")
        if state is None:
            error_msg = "ESP32 STATE değeri alınamadı (None)"
            system_logger.error(
                f"Charge start failed: {error_msg}",
                extra={
                    "endpoint": "/api/charge/start",
                    "user_id": user_id,
                    "error_type": "STATE_NONE_ERROR",
                    "status_data": current_status,
                },
            )
            raise ValueError(error_msg)

        # State değerini ESP32State enum ile kontrol et ve validate et
        try:
            esp32_state = ESP32State(state)
            state_name = esp32_state.name
        except ValueError:
            # Geçersiz state değeri (ESP32State enum'unda yok)
            state_name = f"UNKNOWN_{state}"
            esp32_state = None
            error_msg = f"Geçersiz STATE değeri: {state} (beklenen: 0-8 arası)"
            system_logger.error(
                f"Charge start failed: {error_msg}",
                extra={
                    "endpoint": "/api/charge/start",
                    "user_id": user_id,
                    "error_type": "INVALID_STATE_VALUE",
                    "invalid_state": state,
                    "status_data": current_status,
                },
            )
            raise ValueError(error_msg)

        # Sadece EV_CONNECTED (state=3) durumunda authorization gönderilebilir
        if state != ESP32State.EV_CONNECTED.value:
            # State'e göre hata mesajı oluştur
            if state == ESP32State.IDLE.value:
                detail = "Şarj başlatılamaz (State: IDLE). Kablo takılı değil."
            elif state == ESP32State.CABLE_DETECT.value:
                detail = "Şarj başlatılamaz (State: CABLE_DETECT). Araç bağlı değil."
            elif state == ESP32State.READY.value:
                detail = (
                    "Şarj başlatılamaz (State: READY). Authorization zaten verilmiş."
                )
            elif state >= ESP32State.CHARGING.value:
                detail = f"Şarj başlatılamaz (State: {state_name}). Şarj zaten aktif veya hata durumunda."
            else:
                detail = f"Şarj başlatılamaz (State: {state_name}). Sadece EV_CONNECTED durumunda authorization gönderilebilir."

            system_logger.warning(
                f"Charge start rejected: {detail}",
                extra={
                    "endpoint": "/api/charge/start",
                    "user_id": user_id,
                    "current_state": state,
                    "state_name": state_name,
                    "error_type": "INVALID_STATE",
                },
            )
            raise ValueError(detail)

        # Komut gönderilmeden önce son bir kez STATE kontrolü yapalım (race condition önlemi)
        final_status_check = self.bridge.get_status()
        if final_status_check:
            final_state = final_status_check.get("STATE")
            if final_state is not None and final_state != ESP32State.EV_CONNECTED.value:
                # State değişmiş, komut gönderme
                try:
                    final_state_name = ESP32State(final_state).name
                except ValueError:
                    final_state_name = f"UNKNOWN_{final_state}"
                error_msg = (
                    f"State değişti, şarj başlatılamaz (State: {final_state_name})"
                )
                system_logger.warning(
                    f"Charge start rejected: {error_msg}",
                    extra={
                        "endpoint": "/api/charge/start",
                        "user_id": user_id,
                        "initial_state": state,
                        "final_state": final_state,
                        "error_type": "STATE_CHANGED",
                    },
                )
                raise ValueError(error_msg)

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
        invalidate_cache("status:*")
        invalidate_cache("session_current:*")

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
            user_id: User ID (audit trail için)
            api_key: API key (audit trail için)

        Returns:
            Success response dict

        Raises:
            HTTPException: Business logic hataları için
        """
        # User ID'yi al (audit trail için)
        if not user_id:
            from api.config import config
            user_id = config.get_user_id()

        # Kritik işlemleri logla (şarj durdurma)
        if user_id:
            log_event(
                event_type="charge_stop",
                event_data={
                    "user_id": user_id,
                    "api_key": api_key[:10] + "..." if api_key else None,
                    "timestamp": datetime.now().isoformat(),
                },
                level=logging.INFO,
            )

        if not self.bridge or not self.bridge.is_connected:
            error_msg = "ESP32 bağlantısı yok"
            system_logger.error(
                f"Charge stop failed: {error_msg}",
                extra={
                    "endpoint": "/api/charge/stop",
                    "user_id": user_id,
                    "error_type": "ESP32_CONNECTION_ERROR",
                },
            )
            raise ValueError(error_msg)

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
        invalidate_cache("status:*")
        invalidate_cache("session_current:*")
        invalidate_cache("sessions_list:*")

        return {
            "success": True,
            "message": "Şarj durdurma komutu gönderildi",
            "data": {"command": "charge_stop"},
        }
