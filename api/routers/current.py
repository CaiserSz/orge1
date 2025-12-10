"""
Current Control Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Current control endpoints
"""

import os
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, status, Depends
from esp32.bridge import ESP32Bridge
from api.auth import verify_api_key
from api.event_detector import ESP32State
from api.logging_config import log_event, system_logger
from api.rate_limiting import charge_rate_limit
from api.routers.dependencies import get_bridge
from api.models import APIResponse, CurrentSetRequest

router = APIRouter(prefix="/api", tags=["Current Control"])


@router.post("/maxcurrent")
@charge_rate_limit()  # Kritik endpoint için sıkı rate limit (10/dakika)
async def set_current(
    request_body: CurrentSetRequest,
    request: Request,
    bridge: ESP32Bridge = Depends(get_bridge),
    api_key: str = Depends(verify_api_key),
):
    """
    Maksimum akım ayarlama

    ESP32'ye maksimum akım değerini ayarlar.

    **ÖNEMLİ:** Akım ayarlama sadece aktif şarj başlamadan yapılabilir.
    Şarj esnasında akım değiştirilemez (güvenlik nedeniyle).

    Geçerli akım aralığı: 6-32 amper (herhangi bir tam sayı)
    """
    # User ID'yi al (audit trail için)
    user_id = os.getenv("TEST_API_USER_ID", None)

    # Kritik işlemleri logla (akım ayarlama)
    if user_id:
        log_event(
            event_type="current_set",
            event_data={
                "user_id": user_id,
                "amperage": request_body.amperage,
                "api_key": api_key[:10] + "..." if api_key else None,
                "timestamp": datetime.now().isoformat(),
            },
            level=logging.INFO,
        )

    if not bridge or not bridge.is_connected:
        error_msg = "ESP32 bağlantısı yok"
        system_logger.error(
            f"Current set failed: {error_msg}",
            extra={
                "endpoint": "/api/maxcurrent",
                "user_id": user_id,
                "amperage": request_body.amperage,
                "error_type": "ESP32_CONNECTION_ERROR",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
        )

    # Mevcut durumu kontrol et
    current_status = bridge.get_status()
    if current_status:
        # STATE değerini al ve None kontrolü yap
        state = current_status.get("STATE")
        if state is None:
            # STATE None ise, akım ayarlama işlemini devam ettirebiliriz
            # Ancak loglama yapalım
            system_logger.warning(
                "Current set: STATE değeri None, akım ayarlama devam ediyor",
                extra={
                    "endpoint": "/api/maxcurrent",
                    "user_id": user_id,
                    "amperage": request_body.amperage,
                    "error_type": "STATE_NONE_WARNING",
                    "status_data": current_status,
                },
            )
        else:
            # STATE değerini ESP32State enum ile validate et
            try:
                esp32_state = ESP32State(state)
                state_name = esp32_state.name
            except ValueError:
                # Geçersiz state değeri
                state_name = f"UNKNOWN_{state}"
                error_msg = f"Geçersiz STATE değeri: {state} (beklenen: 0-8 arası)"
                system_logger.error(
                    f"Current set failed: {error_msg}",
                    extra={
                        "endpoint": "/api/maxcurrent",
                        "user_id": user_id,
                        "amperage": request_body.amperage,
                        "error_type": "INVALID_STATE_VALUE",
                        "invalid_state": state,
                        "status_data": current_status,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
                )

            # STATE < CHARGING: Akım ayarlanabilir (IDLE, CABLE_DETECT, EV_CONNECTED, READY)
            # STATE >= CHARGING: Aktif şarj veya hata durumları (akım değiştirilemez)
            # Eğer şarj aktifse veya hata durumundaysa (STATE >= CHARGING) hata döndür
            if (
                state >= ESP32State.CHARGING.value
            ):  # STATE >= CHARGING aktif şarj veya hata durumu
                error_msg = f"Şarj aktifken akım değiştirilemez (State: {state_name})"
                system_logger.warning(
                    f"Current set rejected: {error_msg}",
                    extra={
                        "endpoint": "/api/maxcurrent",
                        "user_id": user_id,
                        "amperage": request_body.amperage,
                        "current_state": state,
                        "state_name": state_name,
                        "error_type": "INVALID_STATE",
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
                )

    # Akım set komutu gönder
    success = bridge.send_current_set(request_body.amperage)

    if not success:
        error_msg = f"Akım ayarlama komutu gönderilemedi ({request.amperage}A)"
        system_logger.error(
            f"Current set failed: {error_msg}",
            extra={
                "endpoint": "/api/maxcurrent",
                "user_id": user_id,
                "amperage": request_body.amperage,
                "error_type": "COMMAND_SEND_ERROR",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )

    return APIResponse(
        success=True,
        message=f"Akım ayarlandı: {request.amperage}A",
        data={"amperage": request.amperage, "command": "current_set"},
    )


@router.get("/current/available")
async def get_available_currents():
    """
    Kullanılabilir akım değerlerini listele

    ESP32'de ayarlanabilir akım aralığını döndürür.
    """
    return APIResponse(
        success=True,
        message="Kullanılabilir akım aralığı",
        data={
            "range": "6-32 amper",
            "min": 6,
            "max": 32,
            "unit": "amper",
            "note": "6-32 aralığında herhangi bir tam sayı değer kullanılabilir",
            "recommended": 16,
            "common_values": [6, 10, 13, 16, 20, 25, 32],
        },
    )
