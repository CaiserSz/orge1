"""
AC Charger REST API
Created: 2025-12-08
Last Modified: 2025-12-09
Version: 1.1.0
Description: ESP32 kontrolü için REST API endpoint'leri
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# ESP32 bridge modülünü import etmek için path ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# .env dosyasından environment variable'ları yükle
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv yüklü değilse, manuel olarak .env dosyasını oku
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

from fastapi import FastAPI, HTTPException, status, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field
from esp32.bridge import get_esp32_bridge, ESP32Bridge
from api.station_info import save_station_info, get_station_info
from api.logging_config import api_logger, log_api_request, system_logger, log_event
from api.auth import verify_api_key
from api.event_detector import get_event_detector
import logging

# FastAPI uygulaması
app = FastAPI(
    title="AC Charger API",
    description="ESP32 şarj istasyonu kontrolü için REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Dependency injection için bridge getter
def get_bridge() -> ESP32Bridge:
    """
    ESP32 bridge instance'ı dependency injection için

    Returns:
        ESP32Bridge instance
    """
    return get_esp32_bridge()


# API Request Logging Middleware
class APILoggingMiddleware(BaseHTTPMiddleware):
    """API isteklerini loglayan middleware"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # İstemci IP adresini al
        client_ip = request.client.host if request.client else None

        # User ID'yi environment variable'dan al (audit trail için)
        user_id = os.getenv("TEST_API_USER_ID", None)

        # İsteği işle
        response = await call_next(request)

        # Yanıt süresini hesapla
        process_time = (time.time() - start_time) * 1000  # milisaniye

        # Logla (şarj başlatma/bitirme hariç)
        if request.url.path not in ["/api/charge/start", "/api/charge/stop"]:
            try:
                log_api_request(
                    method=request.method,
                    path=request.url.path,
                    client_ip=client_ip,
                    status_code=response.status_code,
                    response_time_ms=process_time,
                    user_id=user_id
                )
            except Exception as e:
                # Logging hatası API response'u etkilememeli
                # Sessizce geç (veya fallback logging)
                pass

        return response


# Middleware'i ekle
app.add_middleware(APILoggingMiddleware)

# Static files için mount (logo ve diğer statik dosyalar için)
static_dir = Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında ESP32 bridge'i başlat ve event detector'ı başlat"""
    try:
        bridge = get_esp32_bridge()
        if not bridge.is_connected:
            system_logger.warning("ESP32 bağlantısı başlatılamadı")
        else:
            system_logger.info("ESP32 bridge başarıyla başlatıldı")

        # Event detector'ı başlat
        event_detector = get_event_detector(get_esp32_bridge)
        event_detector.start_monitoring()
        system_logger.info("Event detector başlatıldı")
    except Exception as e:
        system_logger.error(f"Startup hatası: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapanışında event detector'ı durdur ve ESP32 bridge'i kapat"""
    try:
        # Event detector'ı durdur
        try:
            event_detector = get_event_detector(get_esp32_bridge)
            event_detector.stop_monitoring()
            system_logger.info("Event detector durduruldu")
        except Exception as e:
            system_logger.warning(f"Event detector durdurma hatası: {e}")

        # ESP32 bridge'i kapat
        bridge = get_esp32_bridge()
        if bridge and bridge.is_connected:
            bridge.disconnect()
            system_logger.info("ESP32 bridge kapatıldı")
    except Exception as e:
        system_logger.error(f"Shutdown hatası: {e}", exc_info=True)


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
        "docs": "/docs",
        "form": "/form"
    }


@app.get("/form", tags=["Form"], response_class=HTMLResponse)
async def station_form():
    """Şarj istasyonu bilgileri formu"""
    form_path = Path(__file__).parent.parent / "station_form.html"
    if form_path.exists():
        return FileResponse(form_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form dosyası bulunamadı"
        )


@app.get("/api/health", tags=["Health"])
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


@app.get("/api/status", tags=["Status"])
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


@app.post("/api/charge/start", tags=["Charge Control"])
async def start_charge(
    request: ChargeStartRequest,
    bridge: ESP32Bridge = Depends(get_bridge),
    api_key: str = Depends(verify_api_key)
):
    """
    Şarj başlatma

    ESP32'ye authorization komutu gönderir ve şarj izni verir.

    **ÖNEMLİ:** Sadece EV_CONNECTED (State=3) durumunda çalışır.
    Diğer state'lerde hata döndürülür.
    """
    # User ID'yi al (audit trail için)
    user_id = os.getenv("TEST_API_USER_ID", None)

    # Kritik işlemleri logla (şarj başlatma)
    if user_id:
        log_event(
            event_type="charge_start",
            event_data={
                "user_id": user_id,
                "api_key": api_key[:10] + "..." if api_key else None,
                "timestamp": datetime.now().isoformat()
            },
            level=logging.INFO
        )

    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )

    # Mevcut durumu kontrol et
    current_status = bridge.get_status()
    if not current_status:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 durum bilgisi alınamadı"
        )

    state = current_status.get('STATE', 0)

    # STATE=1: IDLE (kablo takılı değil, şarj başlatılamaz)
    # STATE=2: CABLE_DETECT (kablo algılandı, şarj başlatılamaz)
    # STATE=3: EV_CONNECTED (araç bağlı, şarj başlatılabilir) ✅
    # STATE=4: SARJA_HAZIR (şarja hazır, şarj başlatılamaz - authorization zaten verilmiş)
    # STATE=5+: Aktif şarj veya hata durumları (şarj başlatılamaz)

    # Sadece EV_CONNECTED (state=3) durumunda authorization gönderilebilir
    if state != 3:  # EV_CONNECTED
        state_names = {
            1: "IDLE",
            2: "CABLE_DETECT",
            4: "READY",
            5: "CHARGING",
            6: "PAUSED",
            7: "STOPPED",
            8: "FAULT_HARD"
        }
        state_name = state_names.get(state, f"UNKNOWN_{state}")

        if state == 1:
            detail = "Şarj başlatılamaz (State: IDLE). Kablo takılı değil."
        elif state == 2:
            detail = "Şarj başlatılamaz (State: CABLE_DETECT). Araç bağlı değil."
        elif state == 4:
            detail = "Şarj başlatılamaz (State: READY). Authorization zaten verilmiş."
        elif state >= 5:
            detail = f"Şarj başlatılamaz (State: {state_name}). Şarj zaten aktif veya hata durumunda."
        else:
            detail = f"Şarj başlatılamaz (State: {state_name}). Sadece EV_CONNECTED durumunda authorization gönderilebilir."

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

    # Authorization komutu gönder (sadece EV_CONNECTED durumunda)
    success = bridge.send_authorization()

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
async def stop_charge(
    request: ChargeStopRequest,
    bridge: ESP32Bridge = Depends(get_bridge),
    api_key: str = Depends(verify_api_key)
):
    """
    Şarj durdurma

    ESP32'ye charge stop komutu gönderir ve şarjı sonlandırır.
    """
    # User ID'yi al (audit trail için)
    user_id = os.getenv("TEST_API_USER_ID", None)

    # Kritik işlemleri logla (şarj durdurma)
    if user_id:
        log_event(
            event_type="charge_stop",
            event_data={
                "user_id": user_id,
                "api_key": api_key[:10] + "..." if api_key else None,
                "timestamp": datetime.now().isoformat()
            },
            level=logging.INFO
        )

    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )

    # Charge stop komutu gönder
    success = bridge.send_charge_stop()

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
async def set_current(
    request: CurrentSetRequest,
    bridge: ESP32Bridge = Depends(get_bridge),
    api_key: str = Depends(verify_api_key)
):
    """
    Maksimum akım ayarlama

    ESP32'ye maksimum akım değerini ayarlar.

    **ÖNEMLİ:** Akım ayarlama sadece aktif şarj başlamadan yapılabilir.
    Şarj esnasında akım değiştirilemez (güvenlik nedeniyle).

    Geçerli akım aralığı: 6-32 amper (herhangi bir tam sayı)
    """
    # User ID'yi al (audit trail için)
    user_id = os.getenv("TEST_API_USER_ID", None)

    # Kritik işlemleri logla (akım ayarlama)
    if user_id:
        log_event(
            event_type="current_set",
            event_data={
                "user_id": user_id,
                "amperage": request.amperage,
                "api_key": api_key[:10] + "..." if api_key else None,
                "timestamp": datetime.now().isoformat()
            },
            level=logging.INFO
        )

    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok"
        )

    # Mevcut durumu kontrol et
    current_status = bridge.get_status()
    if current_status:
        state = current_status.get('STATE', 0)
        # STATE=1: IDLE (akım ayarlanabilir)
        # STATE=2: CABLE_DETECT (kablo algılandı, akım ayarlanabilir)
        # STATE=3: EV_CONNECTED (araç bağlı, akım ayarlanabilir)
        # STATE=4: SARJA_HAZIR (şarja hazır, akım ayarlanabilir)
        # STATE=5+: Aktif şarj veya hata durumları (akım değiştirilemez)
        # Eğer şarj aktifse veya hata durumundaysa (STATE >= 5) hata döndür
        if state >= 5:  # STATE >= 5 aktif şarj veya hata durumu
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Şarj aktifken akım değiştirilemez (State: {state})"
            )

    # Akım set komutu gönder
    success = bridge.send_current_set(request.amperage)

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
    """
    Global hata yakalayıcı

    Production'da detaylı hata mesajları gizlenir (güvenlik).
    DEBUG mode aktifse detaylı bilgi gösterilir.
    """
    # DEBUG mode kontrolü
    is_debug = os.getenv("DEBUG", "false").lower() == "true"

    # Detaylı hata bilgisini logla (her zaman)
    system_logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        exc_info=True,
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "client_ip": request.client.host if request.client else None
        }
    )

    # Kullanıcıya gösterilecek mesaj
    if is_debug:
        # DEBUG mode: Detaylı hata mesajı
        message = f"Internal server error: {type(exc).__name__}: {str(exc)}"
    else:
        # Production: Genel hata mesajı
        message = "Internal server error occurred"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.get("/api/test/key", tags=["Test"])
async def get_test_api_key():
    """
    Test sayfası için API key'i döndürür

    NOT: Bu endpoint sadece test amaçlıdır. Production'da devre dışı bırakılmalıdır.
    """
    # Production'da bu endpoint'i devre dışı bırak
    environment = os.getenv("ENVIRONMENT", "production").lower()
    if environment == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found"
        )

    # Test amaçlı - sadece development ortamında kullanılmalı
    api_key = os.getenv("SECRET_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured"
        )

    return {
        "api_key": api_key,
        "user_id": os.getenv("TEST_API_USER_ID", ""),
        "note": "This endpoint is for testing purposes only. Disabled in production."
    }


@app.get("/test", response_class=HTMLResponse, tags=["Test"])
async def api_test_page():
    """
    API test sayfası

    Dışarıdan API'leri test etmek için web arayüzü
    """
    test_page_path = Path(__file__).parent.parent / "api_test.html"
    if test_page_path.exists():
        return FileResponse(test_page_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test page not found"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

