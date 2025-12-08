"""
AC Charger REST API
Created: 2025-12-08
Last Modified: 2025-12-08
Version: 1.0.0
Description: ESP32 kontrolü için REST API endpoint'leri
"""

import sys
import os

# ESP32 bridge modülünü import etmek için path ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from esp32.bridge import get_esp32_bridge
from api.station_info import save_station_info, get_station_info

# FastAPI uygulaması
app = FastAPI(
    title="AC Charger API",
    description="ESP32 şarj istasyonu kontrolü için REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ESP32 bridge instance
esp32_bridge = None


@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında ESP32 bridge'i başlat"""
    global esp32_bridge
    try:
        esp32_bridge = get_esp32_bridge()
        if not esp32_bridge.is_connected:
            print("ESP32 bağlantısı başlatılamadı")
    except Exception as e:
        print(f"ESP32 bridge başlatma hatası: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapanışında ESP32 bridge'i kapat"""
    global esp32_bridge
    if esp32_bridge:
        esp32_bridge.disconnect()


# Request/Response modelleri
class ChargeStartRequest(BaseModel):
    """Şarj başlatma isteği"""
    pass


class ChargeStopRequest(BaseModel):
    """Şarj durdurma isteği"""
    pass


class CurrentSetRequest(BaseModel):
    """Akım ayarlama isteği"""
    amperage: int = Field(..., ge=6, le=32, description="Akım değeri (6-32 amper aralığında herhangi bir tam sayı)")


class APIResponse(BaseModel):
    """Genel API yanıt modeli"""
    success: bool
    message: str
    data: Optional[Any] = None  # Dict, List veya başka herhangi bir tip olabilir
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# API Endpoint'leri

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "name": "AC Charger API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Sistem sağlık kontrolü"""
    global esp32_bridge
    
    health_data = {
        "api": "healthy",
        "esp32_connected": False,
        "esp32_status": None
    }
    
    if esp32_bridge:
        health_data["esp32_connected"] = esp32_bridge.is_connected
        if esp32_bridge.is_connected:
            status_data = esp32_bridge.get_status()
            health_data["esp32_status"] = "available" if status_data else "no_status"
    
    return APIResponse(
        success=True,
        message="System health check",
        data=health_data
    )


@app.get("/api/status", tags=["Status"])
async def get_status():
    """
    ESP32 durum bilgisini al
    
    ESP32'den son durum bilgisini döndürür. 
    ESP32 her 5 saniyede bir otomatik olarak durum gönderir.
    """
    global esp32_bridge
    
    if not esp32_bridge or not esp32_bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )
    
    status_data = esp32_bridge.get_status()
    
    if not status_data:
        # Status komutu gönder ve bekle
        status_data = esp32_bridge.get_status_sync(timeout=2.0)
    
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


@app.post("/api/charge/start", tags=["Charge Control"])
async def start_charge(request: ChargeStartRequest):
    """
    Şarj başlatma
    
    ESP32'ye authorization komutu gönderir ve şarj izni verir.
    """
    global esp32_bridge
    
    if not esp32_bridge or not esp32_bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )
    
    # Mevcut durumu kontrol et
    current_status = esp32_bridge.get_status()
    if current_status:
        state = current_status.get('STATE', 0)
        # Eğer zaten şarj ediliyorsa hata döndür
        if state > 0:  # State > 0 genellikle aktif şarj anlamına gelir
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Şarj zaten aktif (State: {state})"
            )
    
    # Authorization komutu gönder
    success = esp32_bridge.send_authorization()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Şarj başlatma komutu gönderilemedi"
        )
    
    return APIResponse(
        success=True,
        message="Şarj başlatma komutu gönderildi",
        data={"command": "authorization"}
    )


@app.post("/api/charge/stop", tags=["Charge Control"])
async def stop_charge(request: ChargeStopRequest):
    """
    Şarj durdurma
    
    ESP32'ye charge stop komutu gönderir ve şarjı sonlandırır.
    """
    global esp32_bridge
    
    if not esp32_bridge or not esp32_bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )
    
    # Charge stop komutu gönder
    success = esp32_bridge.send_charge_stop()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Şarj durdurma komutu gönderilemedi"
        )
    
    return APIResponse(
        success=True,
        message="Şarj durdurma komutu gönderildi",
        data={"command": "charge_stop"}
    )


@app.post("/api/maxcurrent", tags=["Current Control"])
async def set_current(request: CurrentSetRequest):
    """
    Maksimum akım ayarlama
    
    ESP32'ye maksimum akım değerini ayarlar.
    
    **ÖNEMLİ:** Akım ayarlama sadece aktif şarj başlamadan yapılabilir.
    Şarj esnasında akım değiştirilemez (güvenlik nedeniyle).
    
    Geçerli akım aralığı: 6-32 amper (herhangi bir tam sayı)
    """
    global esp32_bridge
    
    if not esp32_bridge or not esp32_bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )
    
    # Mevcut durumu kontrol et
    current_status = esp32_bridge.get_status()
    if current_status:
        state = current_status.get('STATE', 0)
        # Eğer şarj aktifse hata döndür
        if state > 0:  # State > 0 genellikle aktif şarj anlamına gelir
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Şarj aktifken akım değiştirilemez (State: {state})"
            )
    
    # Akım set komutu gönder
    success = esp32_bridge.send_current_set(request.amperage)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Akım ayarlama komutu gönderilemedi ({request.amperage}A)"
        )
    
    return APIResponse(
        success=True,
        message=f"Akım ayarlandı: {request.amperage}A",
        data={"amperage": request.amperage, "command": "current_set"}
    )


@app.get("/api/current/available", tags=["Current Control"])
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
            "common_values": [6, 10, 13, 16, 20, 25, 32]
        }
    )


# Station Information Endpoints

@app.get("/api/station/info", tags=["Station"])
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


@app.post("/api/station/info", tags=["Station"])
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


# Eski endpoint'leri kaldır - gereksiz karmaşıklık
# Aşağıdaki endpoint'ler kaldırıldı:
# - POST /api/stations
# - GET /api/stations
# - GET /api/stations/{station_id}
# - PUT /api/stations/{station_id}
# - DELETE /api/stations/{station_id}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global hata yakalayıcı"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": f"Internal server error: {str(exc)}",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    """
    return HTMLResponse(content=html_content)




@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global hata yakalayıcı"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": f"Internal server error: {str(exc)}",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

