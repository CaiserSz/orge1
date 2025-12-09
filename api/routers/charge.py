"""
Charge Control Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Charge control endpoints (start/stop)
"""

import os
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from esp32.bridge import ESP32Bridge
from api.auth import verify_api_key
from api.logging_config import log_event
from api.routers.dependencies import get_bridge
from api.models import APIResponse, ChargeStartRequest, ChargeStopRequest

router = APIRouter(prefix="/api/charge", tags=["Charge Control"])


@router.post("/start")
async def start_charge(
    request: ChargeStartRequest,
    bridge: ESP32Bridge = Depends(get_bridge),
    api_key: str = Depends(verify_api_key)
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
                "timestamp": datetime.now().isoformat()
            },
            level=logging.INFO
        )

    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )

    # Mevcut durumu kontrol et
    current_status = bridge.get_status()
    if not current_status:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 durum bilgisi alınamadı"
        )

    state = current_status.get('STATE', 0)

    # STATE=1: IDLE (kablo takılı değil, şarj başlatılamaz)
    # STATE=2: CABLE_DETECT (kablo algılandı, şarj başlatılamaz)
    # STATE=3: EV_CONNECTED (araç bağlı, şarj başlatılabilir) ✅
    # STATE=4: SARJA_HAZIR (şarja hazır, şarj başlatılamaz - authorization zaten verilmiş)
    # STATE=5+: Aktif şarj veya hata durumları (şarj başlatılamaz)

    # Sadece EV_CONNECTED (state=3) durumunda authorization gönderilebilir
    if state != 3:  # EV_CONNECTED
        state_names = {
            1: "IDLE",
            2: "CABLE_DETECT",
            4: "READY",
            5: "CHARGING",
            6: "PAUSED",
            7: "STOPPED",
            8: "FAULT_HARD"
        }
        state_name = state_names.get(state, f"UNKNOWN_{state}")

        if state == 1:
            detail = "Şarj başlatılamaz (State: IDLE). Kablo takılı değil."
        elif state == 2:
            detail = "Şarj başlatılamaz (State: CABLE_DETECT). Araç bağlı değil."
        elif state == 4:
            detail = "Şarj başlatılamaz (State: READY). Authorization zaten verilmiş."
        elif state >= 5:
            detail = f"Şarj başlatılamaz (State: {state_name}). Şarj zaten aktif veya hata durumunda."
        else:
            detail = f"Şarj başlatılamaz (State: {state_name}). Sadece EV_CONNECTED durumunda authorization gönderilebilir."

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

    # Authorization komutu gönder (sadece EV_CONNECTED durumunda)
    success = bridge.send_authorization()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Şarj başlatma komutu gönderilemedi"
        )

    return APIResponse(
        success=True,
        message="Şarj başlatma komutu gönderildi",
        data={"command": "authorization"}
    )


@router.post("/stop")
async def stop_charge(
    request: ChargeStopRequest,
    bridge: ESP32Bridge = Depends(get_bridge),
    api_key: str = Depends(verify_api_key)
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
                "timestamp": datetime.now().isoformat()
            },
            level=logging.INFO
        )

    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )

    # Charge stop komutu gönder
    success = bridge.send_charge_stop()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Şarj durdurma komutu gönderilemedi"
        )

    return APIResponse(
        success=True,
        message="Şarj durdurma komutu gönderildi",
        data={"command": "charge_stop"}
    )

