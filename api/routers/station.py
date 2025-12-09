"""
Station Information Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Station information endpoints
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from api.station_info import save_station_info, get_station_info
from api.models import APIResponse

router = APIRouter(prefix="/api/station", tags=["Station"])


@router.get("/info")
async def get_station_info_endpoint():
    """
    Şarj istasyonu bilgilerini al

    Formdan girilen istasyon bilgilerini döndürür.
    """
    station_info = get_station_info()

    if not station_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="İstasyon bilgisi bulunamadı. Lütfen önce formu doldurun."
        )

    return APIResponse(
        success=True,
        message="İstasyon bilgisi alındı",
        data=station_info
    )


@router.post("/info")
async def save_station_info_endpoint(station_data: Dict[str, Any]):
    """
    Şarj istasyonu bilgilerini kaydet

    Formdan girilen istasyon bilgilerini kaydeder.
    """
    if save_station_info(station_data):
        return APIResponse(
            success=True,
            message="İstasyon bilgileri kaydedildi",
            data=station_data
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="İstasyon bilgileri kaydedilemedi"
        )

