"""
Current Control Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Current control endpoints
"""

import os

from fastapi import APIRouter, HTTPException, Request, status, Depends

from api.auth import verify_api_key
from api.models import APIResponse, CurrentSetRequest
from api.rate_limiting import charge_rate_limit
from api.routers.dependencies import get_bridge
from api.services.current_service import CurrentService
from api.cache import cache_response
from esp32.bridge import ESP32Bridge

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
    # Service layer kullan
    current_service = CurrentService(bridge)
    user_id = os.getenv("TEST_API_USER_ID", None)

    try:
        result = current_service.set_current(request_body, user_id, api_key)
        return APIResponse(**result)
    except ValueError as e:
        # Business logic hataları için uygun HTTP exception'a dönüştür
        error_msg = str(e)
        if "ESP32 bağlantısı yok" in error_msg or "Geçersiz STATE değeri" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
            )
        elif "akım değiştirilemez" in error_msg or "State:" in error_msg:
            # State validation hataları için 400 Bad Request
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
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


@router.get("/current/available")
@cache_response(
    ttl=3600, key_prefix="current_available"
)  # 1 saat cache (sabit değerler)
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
