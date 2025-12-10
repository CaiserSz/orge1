"""
Current Control Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Current control endpoints
"""

from fastapi import APIRouter, Request, Depends

from api.auth import verify_api_key
from api.error_handlers import handle_api_errors
from api.models import APIResponse, CurrentSetRequest
from api.rate_limiting import charge_rate_limit
from api.routers.dependencies import get_bridge
from api.services.current_service import CurrentService
from api.cache import cache_response
from esp32.bridge import ESP32Bridge

router = APIRouter(prefix="/api", tags=["Current Control"])


@router.post("/maxcurrent")
@charge_rate_limit()  # Kritik endpoint için sıkı rate limit (10/dakika)
@handle_api_errors
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

    result = current_service.set_current(request_body, user_id=None, api_key=api_key)
    return APIResponse(**result)


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
