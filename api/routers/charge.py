"""
Charge Control Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Charge control endpoints (start/stop)
"""

from fastapi import APIRouter, Depends, Request

from api.auth import verify_api_key
from api.error_handlers import handle_api_errors
from api.models import APIResponse, ChargeStartRequest, ChargeStopRequest
from api.rate_limiting import charge_rate_limit
from api.routers.dependencies import get_bridge
from api.services.charge_service import ChargeService
from esp32.bridge import ESP32Bridge

router = APIRouter(prefix="/api/charge", tags=["Charge Control"])


@router.post("/start")
@charge_rate_limit()  # Charge endpoint'leri için sıkı rate limit (10/dakika)
@handle_api_errors
async def start_charge(
    request_body: ChargeStartRequest,
    request: Request,
    bridge: ESP32Bridge = Depends(get_bridge),
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """
    Şarj başlatma

    ESP32'ye authorization komutu gönderir ve şarj izni verir.

    **ÖNEMLİ:** Sadece EV_CONNECTED (State=3) durumunda çalışır.
    Diğer state'lerde hata döndürülür.
    """
    # Service layer kullan
    charge_service = ChargeService(bridge)

    # Request body'den user_id'yi al (varsa)
    user_id = request_body.user_id if request_body.user_id else None
    result = charge_service.start_charge(request_body, user_id=user_id, api_key=api_key)
    return APIResponse(**result)


@router.post("/stop")
@charge_rate_limit()  # Charge endpoint'leri için sıkı rate limit (10/dakika)
@handle_api_errors
async def stop_charge(
    request_body: ChargeStopRequest,
    request: Request,
    bridge: ESP32Bridge = Depends(get_bridge),
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """
    Şarj durdurma

    ESP32'ye charge stop komutu gönderir ve şarjı sonlandırır.
    """
    # Service layer kullan
    charge_service = ChargeService(bridge)

    # Request body'den user_id'yi al (varsa)
    user_id = request_body.user_id if request_body.user_id else None
    result = charge_service.stop_charge(request_body, user_id=user_id, api_key=api_key)
    return APIResponse(**result)
