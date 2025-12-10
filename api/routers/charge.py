"""
Charge Control Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Charge control endpoints (start/stop)
"""

import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.auth import verify_api_key
from api.event_detector import ESP32State
from api.logging_config import log_event, system_logger
from api.models import APIResponse, ChargeStartRequest, ChargeStopRequest
from api.rate_limiting import charge_rate_limit
from api.routers.dependencies import get_bridge
from api.cache import invalidate_cache
from esp32.bridge import ESP32Bridge

router = APIRouter(prefix="/api/charge", tags=["Charge Control"])


@router.post("/start")
@charge_rate_limit()  # Charge endpoint'leri için sıkı rate limit (10/dakika)
async def start_charge(
    request_body: ChargeStartRequest,
    request: Request,
    bridge: ESP32Bridge = Depends(get_bridge),
    api_key: str = Depends(verify_api_key),
):
    """
    Şarj başlatma

    ESP32'ye authorization komutu gönderir ve şarj izni verir.

    **ÖNEMLİ:** Sadece EV_CONNECTED (State=3) durumunda çalışır.
    Diğer state'lerde hata döndürülür.
    """
    # User ID'yi al (audit trail için)
    user_id = os.getenv("TEST_API_USER_ID", None)

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

    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok",
        )

    # Mevcut durumu kontrol et
    current_status = bridge.get_status()
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
        )

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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
        )

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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
        )

    # Sadece EV_CONNECTED (state=3) durumunda authorization gönderilebilir
    # Not: Buraya geldiysek state geçerli bir ESP32State değeridir (yukarıda validate edildi)
    if state != ESP32State.EV_CONNECTED.value:
        # State'e göre hata mesajı oluştur
        if state == ESP32State.IDLE.value:
            detail = "Şarj başlatılamaz (State: IDLE). Kablo takılı değil."
        elif state == ESP32State.CABLE_DETECT.value:
            detail = "Şarj başlatılamaz (State: CABLE_DETECT). Araç bağlı değil."
        elif state == ESP32State.READY.value:
            detail = "Şarj başlatılamaz (State: READY). Authorization zaten verilmiş."
        elif state >= ESP32State.CHARGING.value:
            detail = f"Şarj başlatılamaz (State: {state_name}). Şarj zaten aktif veya hata durumunda."
        else:
            # Bu durum teorik olarak olmamalı (yukarıda validate edildi)
            # Ancak güvenlik için ek kontrol
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    # Authorization komutu gönder (sadece EV_CONNECTED durumunda)
    # Not: Buraya geldiysek state == EV_CONNECTED.value (yukarıda kontrol edildi)
    # Komut gönderilmeden önce son bir kez STATE kontrolü yapalım (race condition önlemi)
    final_status_check = bridge.get_status()
    if final_status_check:
        final_state = final_status_check.get("STATE")
        if final_state is not None and final_state != ESP32State.EV_CONNECTED.value:
            # State değişmiş, komut gönderme
            try:
                final_state_name = ESP32State(final_state).name
            except ValueError:
                final_state_name = f"UNKNOWN_{final_state}"
            error_msg = f"State değişti, şarj başlatılamaz (State: {final_state_name})"
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )

    success = bridge.send_authorization()

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )

    # Status ve session cache'lerini invalidate et (state değişti)
    invalidate_cache("status:*")
    invalidate_cache("session_current:*")

    return APIResponse(
        success=True,
        message="Şarj başlatma komutu gönderildi",
        data={"command": "authorization"},
    )


@router.post("/stop")
@charge_rate_limit()  # Charge endpoint'leri için sıkı rate limit (10/dakika)
async def stop_charge(
    request: ChargeStopRequest,
    bridge: ESP32Bridge = Depends(get_bridge),
    api_key: str = Depends(verify_api_key),
):
    """
    Şarj durdurma

    ESP32'ye charge stop komutu gönderir ve şarjı sonlandırır.
    """
    # User ID'yi al (audit trail için)
    user_id = os.getenv("TEST_API_USER_ID", None)

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

    if not bridge or not bridge.is_connected:
        error_msg = "ESP32 bağlantısı yok"
        system_logger.error(
            f"Charge stop failed: {error_msg}",
            extra={
                "endpoint": "/api/charge/stop",
                "user_id": user_id,
                "error_type": "ESP32_CONNECTION_ERROR",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
        )

    # Charge stop komutu gönder
    success = bridge.send_charge_stop()

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )

    # Status ve session cache'lerini invalidate et (state değişti)
    invalidate_cache("status:*")
    invalidate_cache("session_current:*")
    invalidate_cache("sessions_list:*")
    invalidate_cache("user_sessions:*")

    return APIResponse(
        success=True,
        message="Şarj durdurma komutu gönderildi",
        data={"command": "charge_stop"},
    )
