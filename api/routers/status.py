"""
Status Router
Created: 2025-12-10
Last Modified: 2025-12-13 23:25:00
Version: 1.2.0
Description: Status and health check endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.cache import CacheInvalidator, cache_response
from api.event_detector import ESP32State, get_event_detector
from api.metrics import get_metrics_response, update_all_metrics
from api.models import APIResponse
from api.rate_limiting import status_rate_limit
from api.routers.dependencies import get_bridge
from api.services.health_service import build_health_response
from api.services.status_service import StatusService
from api.station_info import get_station_info
from esp32.bridge import ESP32Bridge

router = APIRouter(prefix="/api", tags=["Status"])


@router.get("/health")
@cache_response(ttl=30, key_prefix="health")
async def health_check(bridge: ESP32Bridge = Depends(get_bridge)):
    return build_health_response(bridge, get_bridge)


@router.get("/status")
@status_rate_limit()  # Status endpoint'leri için rate limit (30/dakika)
@cache_response(
    ttl=5, key_prefix="status"
)  # 5 saniye cache (ESP32 7.5 saniyede bir gönderiyor)
async def get_status(request: Request, bridge: ESP32Bridge = Depends(get_bridge)):
    """
    ESP32 durum bilgisini al

    ESP32'den son durum bilgisini döndürür.
    ESP32 her 7.5 saniyede bir otomatik olarak durum gönderir.

    Stale data kontrolü: 10 saniyeden eski veri None döndürülür ve yeni veri istenir.
    """
    # Service layer kullan
    StatusService(bridge)

    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok",
        )

    # Önce cache'den kontrol et (stale data kontrolü ile)
    status_data = bridge.get_status(max_age_seconds=10.0)

    if not status_data:
        # Cache'de veri yok veya çok eski - yeni veri iste
        status_data = bridge.get_status_sync(timeout=2.0)

    if not status_data:
        # Bağlantı bu aşamada kopmuşsa 503 döndür (bağlantı hatası)
        if not bridge.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ESP32 bağlantısı yok",
            )

        # Bağlantı var ama status alınamıyorsa timeout olarak değerlendir
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ESP32'den durum bilgisi alınamadı (timeout veya stale data)",
        )

    # IDLE + kablo yokken MAX değeri standart (station_info.max_current_amp, varsayılan 32A) olmalı.
    # Şarj bitip kablo çıkarıldıktan sonra kullanıcı ayarı (örn. 16A) otomatik resetlenir.
    try:
        state = status_data.get("STATE")
        cable = status_data.get("CABLE")
        current_max = status_data.get("MAX")
        station_info = get_station_info() or {}
        desired_max = int(station_info.get("max_current_amp") or 32)
        desired_max = max(6, min(32, desired_max))

        if (
            state == ESP32State.IDLE.value
            and cable == 0
            and current_max is not None
            and int(current_max) != desired_max
        ):
            if bridge.send_current_set(desired_max):
                status_data["MAX"] = desired_max
                CacheInvalidator.invalidate_status()
    except Exception:
        # Non-critical; status read akışını bozma
        pass

    return APIResponse(
        success=True, message="Status retrieved successfully", data=status_data
    )


@router.get("/metrics")
async def metrics(bridge: ESP32Bridge = Depends(get_bridge)):
    """
    Prometheus metrics endpoint

    Prometheus tarafından scrape edilebilir metrics endpoint'i.
    Tüm sistem metriklerini Prometheus formatında döndürür.
    """
    event_detector = get_event_detector(get_bridge)
    update_all_metrics(bridge=bridge, event_detector=event_detector)
    return get_metrics_response()


@router.get("/alerts")
@cache_response(ttl=10, key_prefix="alerts")  # 10 saniye cache
async def get_alerts(bridge: ESP32Bridge = Depends(get_bridge)):
    """
    Active alerts endpoint

    Sistemdeki aktif alert'leri döndürür.
    """
    from api.alerting import get_alert_manager
    from api.metrics import update_all_metrics

    event_detector = get_event_detector(get_bridge)
    update_all_metrics(bridge=bridge, event_detector=event_detector)

    alert_manager = get_alert_manager()
    alert_manager.evaluate_all(bridge=bridge, event_detector=event_detector)

    active_alerts = alert_manager.get_active_alerts()

    alerts_data = [
        {
            "name": alert.name,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata,
        }
        for alert in active_alerts
    ]

    return APIResponse(
        success=True,
        message=f"Active alerts: {len(active_alerts)}",
        data={
            "active_alerts": alerts_data,
            "count": len(active_alerts),
        },
    )
