"""
AC Charger REST API
Created: 2025-12-08
Last Modified: 2025-12-10 02:30:00
Version: 2.0.0
Description: ESP32 kontrolü için REST API endpoint'leri
"""

import sys
import os
import time
from pathlib import Path
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

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from esp32.bridge import get_esp32_bridge
from api.logging_config import log_api_request, system_logger
from api.event_detector import get_event_detector

# Router'ları import et
from api.routers import charge, status, current, station, test

# FastAPI uygulaması
app = FastAPI(
    title="AC Charger API",
    description="ESP32 şarj istasyonu kontrolü için REST API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Router'ları include et
app.include_router(charge.router)
app.include_router(status.router)
app.include_router(current.router)
app.include_router(station.router)
app.include_router(test.router)


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


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "name": "AC Charger API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "form": "/form"
    }


# Form endpoint
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


# Global exception handler
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
