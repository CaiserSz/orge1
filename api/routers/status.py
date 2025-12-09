"""
Status Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Status and health check endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from esp32.bridge import ESP32Bridge
from api.routers.dependencies import get_bridge
from api.models import APIResponse

router = APIRouter(prefix="/api", tags=["Status"])


@router.get("/health")
async def health_check(bridge: ESP32Bridge = Depends(get_bridge)):
    """Sistem sağlık kontrolü"""
    health_data = {
        "api": "healthy",
        "esp32_connected": False,
        "esp32_status": None
    }

    if bridge:
        health_data["esp32_connected"] = bridge.is_connected
        if bridge.is_connected:
            status_data = bridge.get_status()
            health_data["esp32_status"] = "available" if status_data else "no_status"

    return APIResponse(
        success=True,
        message="System health check",
        data=health_data
    )


@router.get("/status")
async def get_status(bridge: ESP32Bridge = Depends(get_bridge)):
    """
    ESP32 durum bilgisini al

    ESP32'den son durum bilgisini döndürür.
    ESP32 her 5 saniyede bir otomatik olarak durum gönderir.
    """
    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )

    status_data = bridge.get_status()

    if not status_data:
        # Status komutu gönder ve bekle
        status_data = bridge.get_status_sync(timeout=2.0)

    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ESP32'den durum bilgisi alınamadı"
        )

    return APIResponse(
        success=True,
        message="Status retrieved successfully",
        data=status_data
    )

