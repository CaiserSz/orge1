"""
Charge Control Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Charge control endpoints (start/stop)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.auth import verify_api_key
from api.models import APIResponse, ChargeStartRequest, ChargeStopRequest
from api.rate_limiting import charge_rate_limit
from api.routers.dependencies import get_bridge
from api.services.charge_service import ChargeService
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
    # Service layer kullan
    charge_service = ChargeService(bridge)

    try:
        result = charge_service.start_charge(request_body, user_id=None, api_key=api_key)
        return APIResponse(**result)
    except ValueError as e:
        # Business logic hataları için uygun HTTP exception'a dönüştür
        error_msg = str(e)
        if (
            "ESP32 bağlantısı yok" in error_msg
            or "ESP32 durum bilgisi" in error_msg
            or "STATE değeri" in error_msg
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
            )
        elif "Geçersiz STATE değeri" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
            )
        else:
            # State validation hataları için 400 Bad Request
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )
    except Exception as e:
        # Diğer hatalar için 500 Internal Server Error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
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
    # Service layer kullan
    charge_service = ChargeService(bridge)

    try:
        result = charge_service.stop_charge(request, user_id=None, api_key=api_key)
        return APIResponse(**result)
    except ValueError as e:
        # Business logic hataları için uygun HTTP exception'a dönüştür
        error_msg = str(e)
        if "ESP32 bağlantısı yok" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
            )
    except Exception as e:
        # Diğer hatalar için 500 Internal Server Error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
