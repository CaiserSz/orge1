"""
Status Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Status and health check endpoints
"""

import threading
import time
from fastapi import APIRouter, HTTPException, status, Depends
from esp32.bridge import ESP32Bridge
from api.routers.dependencies import get_bridge
from api.models import APIResponse
from api.event_detector import get_event_detector

router = APIRouter(prefix="/api", tags=["Status"])


@router.get("/health")
async def health_check(bridge: ESP32Bridge = Depends(get_bridge)):
    """
    Sistem sağlık kontrolü (Detaylı)

    Sistemin genel sağlık durumunu kontrol eder:
    - API servisi durumu
    - ESP32 bağlantı durumu
    - Event detector durumu
    - Thread sayısı
    - Memory kullanımı (yaklaşık)
    """
    import sys
    import os

    health_data = {
        "api": "healthy",
        "esp32_connected": False,
        "esp32_status": None,
        "event_detector": None,
        "threads": threading.active_count(),
        "memory_mb": None
    }

    # ESP32 durumu
    if bridge:
        health_data["esp32_connected"] = bridge.is_connected
        if bridge.is_connected:
            status_data = bridge.get_status(max_age_seconds=15.0)
            health_data["esp32_status"] = "available" if status_data else "no_status"
        else:
            health_data["esp32_status"] = "disconnected"
            # Reconnection durumu bilgisi
            if hasattr(bridge, '_reconnect_attempts'):
                health_data["reconnect_attempts"] = bridge._reconnect_attempts

    # Event detector durumu
    try:
        event_detector = get_event_detector(get_bridge)
        if event_detector:
            health_data["event_detector"] = {
                "monitoring": event_detector.is_monitoring,
                "thread_alive": event_detector._monitor_thread.is_alive() if event_detector._monitor_thread else False
            }
    except Exception as e:
        health_data["event_detector"] = {"error": str(e)}

    # Memory kullanımı (yaklaşık)
    try:
        import resource
        memory_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        health_data["memory_mb"] = round(memory_kb / 1024, 2)
    except (ImportError, AttributeError):
        # resource modülü mevcut değilse veya maxrss desteklenmiyorsa
        try:
            # Process bilgisini /proc'dan oku (Linux)
            pid = os.getpid()
            with open(f'/proc/{pid}/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        memory_kb = int(line.split()[1])
                        health_data["memory_mb"] = round(memory_kb / 1024, 2)
                        break
        except (OSError, ValueError, FileNotFoundError):
            pass  # Memory bilgisi alınamadı

    # Genel sağlık durumu
    is_healthy = (
        health_data["api"] == "healthy" and
        health_data["esp32_connected"] and
        health_data["esp32_status"] == "available"
    )

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
    ESP32 her 7.5 saniyede bir otomatik olarak durum gönderir.

    Stale data kontrolü: 10 saniyeden eski veri None döndürülür ve yeni veri istenir.
    """
    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )

    # Önce cache'den kontrol et (stale data kontrolü ile)
    status_data = bridge.get_status(max_age_seconds=10.0)

    if not status_data:
        # Cache'de veri yok veya çok eski - yeni veri iste
        status_data = bridge.get_status_sync(timeout=2.0)

    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ESP32'den durum bilgisi alınamadı (timeout veya stale data)"
        )

    return APIResponse(
        success=True,
        message="Status retrieved successfully",
        data=status_data
    )

