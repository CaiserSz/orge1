"""
Meter API Router
Created: 2025-12-10
Last Modified: 2025-12-10
Version: 1.0.0
Description: Meter data endpoints (for testing purposes)
"""

from fastapi import APIRouter, HTTPException, Request, status
from api.models import APIResponse
from api.cache import cache_response
from api.logging_config import system_logger

router = APIRouter(prefix="/api/meter", tags=["Meter"])


@router.get("/status")
@cache_response(ttl=5, key_prefix="meter_status")  # 5 saniye cache
async def get_meter_status(request: Request):
    """
    Meter durum bilgisi

    Meter bağlantı durumu ve son okunan değerleri döndürür.
    Meter aktif değilse veya bağlı değilse bilgi mesajı döndürür.
    """
    try:
        # Meter modülünü import et (opsiyonel)
        try:
            from api.meter import get_meter

            meter = get_meter()

            if not meter:
                return APIResponse(
                    success=True,
                    message="Meter modülü yüklü değil",
                    data={
                        "connected": False,
                        "available": False,
                        "note": "Meter modülü henüz aktif değil",
                    },
                )

            # Meter bağlantı durumu
            # (İlk çağrıda bağlanmayı dene - bağlantı yoksa sorun değil)
            try:
                if (
                    hasattr(meter, "connect")
                    and hasattr(meter, "is_connected")
                    and not meter.is_connected()
                ):
                    meter.connect()
            except Exception:
                pass

            is_connected = (
                meter.is_connected() if hasattr(meter, "is_connected") else False
            )

            if not is_connected:
                return APIResponse(
                    success=True,
                    message="Meter bağlı değil",
                    data={
                        "connected": False,
                        "available": True,
                        "note": "Meter modülü yüklü ancak bağlantı yok",
                    },
                )

            # Meter verilerini oku
            try:
                reading = meter.read_all() if hasattr(meter, "read_all") else None

                if reading and hasattr(reading, "is_valid") and reading.is_valid:
                    meter_data = {
                        "connected": True,
                        "available": True,
                        "voltage_v": getattr(reading, "voltage_v", None),
                        "current_a": getattr(reading, "current_a", None),
                        "power_w": getattr(reading, "power_w", None),
                        "power_kw": getattr(reading, "power_kw", None),
                        "energy_kwh": getattr(reading, "energy_kwh", None),
                        "frequency_hz": getattr(reading, "frequency_hz", None),
                        "power_factor": getattr(reading, "power_factor", None),
                        "timestamp": getattr(reading, "timestamp", None),
                        "phase_values": getattr(reading, "phase_values", None),
                        "totals": getattr(reading, "totals", None),
                    }
                    return APIResponse(
                        success=True,
                        message="Meter verileri başarıyla alındı",
                        data=meter_data,
                    )
                else:
                    return APIResponse(
                        success=True,
                        message="Meter verisi geçersiz",
                        data={
                            "connected": True,
                            "available": True,
                            "valid": False,
                            "note": "Meter bağlı ancak geçerli veri okunamadı",
                        },
                    )
            except Exception as e:
                system_logger.warning(f"Meter read error: {e}", exc_info=True)
                return APIResponse(
                    success=True,
                    message="Meter verisi okunamadı",
                    data={
                        "connected": True,
                        "available": True,
                        "error": str(e),
                        "note": "Meter bağlı ancak veri okuma hatası",
                    },
                )

        except ImportError:
            # Meter modülü yüklü değil
            return APIResponse(
                success=True,
                message="Meter modülü yüklü değil",
                data={
                    "connected": False,
                    "available": False,
                    "note": "Meter modülü henüz aktif değil. Test amaçlı endpoint.",
                },
            )

    except Exception as e:
        system_logger.error(f"Meter status get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Meter bilgisi alınamadı: {str(e)}",
        )


@router.get("/reading")
@cache_response(
    ttl=2, key_prefix="meter_reading"
)  # 2 saniye cache (daha sık güncelleme)
async def get_meter_reading(request: Request):
    """
    Son meter okuması

    Meter'den son okunan değerleri döndürür.
    Meter aktif değilse veya bağlı değilse bilgi mesajı döndürür.
    """
    try:
        # Meter modülünü import et (opsiyonel)
        try:
            from api.meter import get_meter

            meter = get_meter()

            if not meter:
                return APIResponse(
                    success=True,
                    message="Meter modülü yüklü değil",
                    data=None,
                )

            # Meter bağlantı durumu
            # (İlk çağrıda bağlanmayı dene - bağlantı yoksa sorun değil)
            try:
                if (
                    hasattr(meter, "connect")
                    and hasattr(meter, "is_connected")
                    and not meter.is_connected()
                ):
                    meter.connect()
            except Exception:
                pass

            is_connected = (
                meter.is_connected() if hasattr(meter, "is_connected") else False
            )

            if not is_connected:
                return APIResponse(
                    success=True,
                    message="Meter bağlı değil",
                    data=None,
                )

            # Meter verilerini oku
            reading = meter.read_all() if hasattr(meter, "read_all") else None

            if reading and hasattr(reading, "is_valid") and reading.is_valid:
                meter_data = {
                    "voltage_v": getattr(reading, "voltage_v", None),
                    "current_a": getattr(reading, "current_a", None),
                    "power_w": getattr(reading, "power_w", None),
                    "power_kw": getattr(reading, "power_kw", None),
                    "energy_kwh": getattr(reading, "energy_kwh", None),
                    "frequency_hz": getattr(reading, "frequency_hz", None),
                    "power_factor": getattr(reading, "power_factor", None),
                    "timestamp": getattr(reading, "timestamp", None),
                    "phase_values": getattr(reading, "phase_values", None),
                    "totals": getattr(reading, "totals", None),
                }
                return APIResponse(
                    success=True,
                    message="Meter okuması başarıyla alındı",
                    data=meter_data,
                )
            else:
                return APIResponse(
                    success=True,
                    message="Meter verisi geçersiz",
                    data=None,
                )

        except ImportError:
            # Meter modülü yüklü değil
            return APIResponse(
                success=True,
                message="Meter modülü yüklü değil",
                data=None,
            )

    except Exception as e:
        system_logger.error(f"Meter reading get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Meter okuması alınamadı: {str(e)}",
        )
