"""
Station Information Router
Created: 2025-12-10
Last Modified: 2025-12-10 16:00:00
Version: 1.1.0
Description: Station information endpoints
"""

from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from api.station_info import save_station_info, get_station_info
from api.models import APIResponse
from api.cache import cache_response, invalidate_cache
from api.routers.dependencies import get_bridge
from esp32.bridge import ESP32Bridge
from api.session import get_session_manager, SessionStatus

router = APIRouter(prefix="/api/station", tags=["Station"])


@router.get("/info")
@cache_response(
    ttl=3600, key_prefix="station_info"
)  # 1 saat cache (station info nadiren değişir)
async def get_station_info_endpoint() -> APIResponse:
    """
    Şarj istasyonu bilgilerini al

    Formdan girilen istasyon bilgilerini döndürür.
    """
    station_info = get_station_info()

    if not station_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="İstasyon bilgisi bulunamadı. Lütfen önce formu doldurun.",
        )

    return APIResponse(
        success=True, message="İstasyon bilgisi alındı", data=station_info
    )


@router.post("/info")
async def save_station_info_endpoint(station_data: Dict[str, Any]) -> APIResponse:
    """
    Şarj istasyonu bilgilerini kaydet

    Formdan girilen istasyon bilgilerini kaydeder.
    """
    if save_station_info(station_data):
        # Station info cache'ini invalidate et
        invalidate_cache("station_info:*")

        return APIResponse(
            success=True, message="İstasyon bilgileri kaydedildi", data=station_data
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="İstasyon bilgileri kaydedilemedi",
        )


@router.get("/status")
@cache_response(ttl=10, key_prefix="station_status")  # 10 saniye cache
async def get_station_status(
    bridge: ESP32Bridge = Depends(get_bridge),
) -> APIResponse:
    """
    Harita ve mobil uygulama için istasyon durum bilgisi

    Bu endpoint harita ve mobil uygulama için optimize edilmiş tek bir API çağrısıyla
    tüm gerekli bilgileri döndürür:
    - İstasyon bilgileri (konum, adres, vb.)
    - ESP32 durum bilgisi (STATE, STATE_NAME, vb.)
    - Müsaitlik durumu (available/busy/fault/reserved)
    - Aktif session özeti (varsa)
    - İstatistikler (bugün/hafta/ay)
    - Son aktivite zamanı
    - Gerçek zamanlı güç tüketimi (varsa)

    Returns:
        Harita/mobil uygulama için optimize edilmiş istasyon durum bilgisi
    """
    try:
        # 1. İstasyon bilgilerini al
        station_info = get_station_info()
        if not station_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="İstasyon bilgisi bulunamadı. Lütfen önce formu doldurun.",
            )

        # 2. ESP32 durum bilgisini al
        esp32_status = None
        availability_status = "unknown"
        realtime_power_kw = None

        if bridge and bridge.is_connected:
            esp32_status = bridge.get_status(max_age_seconds=15.0)
            if not esp32_status:
                esp32_status = bridge.get_status_sync(timeout=2.0)

            if esp32_status:
                state_name = esp32_status.get("STATE_NAME", "")

                # Müsaitlik durumunu belirle
                if state_name in ["FAULT_HARD", "HARDFAULT_END"]:
                    availability_status = "fault"
                elif state_name in ["CHARGING", "PAUSED"]:
                    availability_status = "busy"
                elif state_name in ["READY", "EV_CONNECTED"]:
                    availability_status = "reserved"
                elif state_name in ["IDLE", "CABLE_DETECT"]:
                    availability_status = "available"
                else:
                    availability_status = "unknown"

                # Gerçek zamanlı güç tüketimi hesapla (yaklaşık)
                # PWM değerinden ve MAX değerinden tahmin edilebilir
                if state_name == "CHARGING":
                    pwm = esp32_status.get("PWM", 0)
                    max_amp = esp32_status.get("MAX", 0)
                    # PWM 0-255 arası, MAX amper cinsinden
                    # Güç = (PWM/255) * MAX * 230V / 1000 (kW) (tek faz için yaklaşık)
                    if pwm > 0 and max_amp > 0:
                        # PWM yüzdesi
                        pwm_percent = (pwm / 255.0) * 100
                        # Aktif akım (PWM yüzdesine göre)
                        active_current = (pwm_percent / 100.0) * max_amp
                        # Güç hesaplama (tek faz, 230V varsayımı)
                        realtime_power_kw = round((active_current * 230) / 1000, 2)

        # 3. Aktif session bilgisini al
        active_session_summary = None
        try:
            session_manager = get_session_manager()
            current_session = session_manager.get_current_session()
            if current_session:
                active_session_summary = {
                    "session_id": current_session.get("session_id"),
                    "start_time": current_session.get("start_time"),
                    "duration_seconds": current_session.get("duration_seconds"),
                    "user_id": current_session.get("user_id"),
                }
        except Exception:
            pass  # Session bilgisi alınamazsa devam et

        # 4. İstatistikleri al
        stats = None
        try:
            session_manager = get_session_manager()
            stats = {
                "total": session_manager.get_session_count(status=None),
                "active": session_manager.get_session_count(
                    status=SessionStatus.ACTIVE
                ),
                "completed": session_manager.get_session_count(
                    status=SessionStatus.COMPLETED
                ),
                "cancelled": session_manager.get_session_count(
                    status=SessionStatus.CANCELLED
                ),
                "faulted": session_manager.get_session_count(
                    status=SessionStatus.FAULTED
                ),
            }
        except Exception:
            pass  # İstatistikler alınamazsa devam et

        # 5. Son aktivite zamanı (ESP32 status timestamp'i)
        last_activity_time = None
        if esp32_status and "timestamp" in esp32_status:
            last_activity_time = esp32_status["timestamp"]

        # 6. Harita/mobil için optimize edilmiş response oluştur
        response_data = {
            # İstasyon bilgileri
            "station": {
                "station_id": station_info.get("station_id"),
                "name": station_info.get("name"),
                "location": station_info.get("location"),
                "address": station_info.get("address"),
                "latitude": station_info.get("latitude"),
                "longitude": station_info.get("longitude"),
                "max_power_kw": station_info.get("max_power_kw"),
                "max_current_amp": station_info.get("max_current_amp"),
                "connector_type": station_info.get("connector_type"),
                "description": station_info.get("description"),
            },
            # Durum bilgileri
            "status": {
                "availability": availability_status,  # available/busy/fault/reserved/unknown
                "state": esp32_status.get("STATE") if esp32_status else None,
                "state_name": esp32_status.get("STATE_NAME") if esp32_status else None,
                "max_current_amp": esp32_status.get("MAX") if esp32_status else None,
                "auth_required": (
                    bool(esp32_status.get("AUTH")) if esp32_status else False
                ),
                "cable_connected": (
                    bool(esp32_status.get("CABLE")) if esp32_status else False
                ),
                "last_activity_time": last_activity_time,
            },
            # Aktif session özeti
            "active_session": active_session_summary,
            # İstatistikler
            "statistics": stats,
            # Gerçek zamanlı güç tüketimi
            "realtime_power_kw": realtime_power_kw,
            # Timestamp
            "timestamp": datetime.now().isoformat(),
        }

        return APIResponse(
            success=True,
            message="İstasyon durum bilgisi alındı",
            data=response_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        from api.logging_config import system_logger

        system_logger.error(f"Station status get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"İstasyon durum bilgisi alınamadı: {str(e)}",
        )
