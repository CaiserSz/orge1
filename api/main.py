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
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Şarj İstasyonu Yönetimi</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                padding: 40px;
            }
            h1 {
                color: #333;
                margin-bottom: 30px;
                text-align: center;
                font-size: 2em;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 500;
            }
            input, select, textarea {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            input:focus, select:focus, textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            textarea {
                resize: vertical;
                min-height: 80px;
            }
            .row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }
            @media (max-width: 600px) {
                .row { grid-template-columns: 1fr; }
            }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 14px 28px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                margin-top: 10px;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            button:active {
                transform: translateY(0);
            }
            .message {
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 20px;
                display: none;
            }
            .message.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .message.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .stations-list {
                margin-top: 40px;
                padding-top: 40px;
                border-top: 2px solid #e0e0e0;
            }
            .station-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 15px;
                border-left: 4px solid #667eea;
            }
            .station-card h3 {
                color: #333;
                margin-bottom: 10px;
            }
            .station-card p {
                color: #666;
                margin: 5px 0;
            }
            .btn-group {
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }
            .btn-group button {
                flex: 1;
                padding: 10px;
                font-size: 14px;
            }
            .btn-edit {
                background: #28a745;
            }
            .btn-delete {
                background: #dc3545;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔌 Şarj İstasyonu Yönetimi</h1>
            
            <div id="message" class="message"></div>
            
            <form id="stationForm">
                <div class="form-group">
                    <label for="station_id">İstasyon ID *</label>
                    <input type="text" id="station_id" name="station_id" required 
                           placeholder="örn: STATION-001">
                </div>
                
                <div class="form-group">
                    <label for="name">İstasyon Adı *</label>
                    <input type="text" id="name" name="name" required 
                           placeholder="örn: Merkez Şarj İstasyonu">
                </div>
                
                <div class="row">
                    <div class="form-group">
                        <label for="location">Konum</label>
                        <input type="text" id="location" name="location" 
                               placeholder="örn: İstanbul">
                    </div>
                    
                    <div class="form-group">
                        <label for="max_current_amp">Maksimum Akım (A)</label>
                        <input type="number" id="max_current_amp" name="max_current_amp" 
                               min="6" max="32" placeholder="6-32">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="address">Adres</label>
                    <textarea id="address" name="address" 
                              placeholder="Tam adres bilgisi"></textarea>
                </div>
                
                <div class="row">
                    <div class="form-group">
                        <label for="max_power_kw">Maksimum Güç (kW)</label>
                        <input type="number" id="max_power_kw" name="max_power_kw" 
                               step="0.1" min="0" placeholder="örn: 22.0">
                    </div>
                    
                    <div class="form-group">
                        <label for="connector_type">Bağlantı Tipi</label>
                        <select id="connector_type" name="connector_type">
                            <option value="">Seçiniz</option>
                            <option value="Type2">Type 2</option>
                            <option value="CCS">CCS</option>
                            <option value="CHAdeMO">CHAdeMO</option>
                            <option value="Tesla">Tesla</option>
                            <option value="Schuko">Schuko</option>
                        </select>
                    </div>
                </div>
                
                <div class="row">
                    <div class="form-group">
                        <label for="latitude">Enlem</label>
                        <input type="number" id="latitude" name="latitude" 
                               step="0.000001" placeholder="41.0082">
                    </div>
                    
                    <div class="form-group">
                        <label for="longitude">Boylam</label>
                        <input type="number" id="longitude" name="longitude" 
                               step="0.000001" placeholder="28.9784">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="status">Durum</label>
                    <select id="status" name="status">
                        <option value="active">Aktif</option>
                        <option value="inactive">Pasif</option>
                        <option value="maintenance">Bakımda</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="description">Açıklama</label>
                    <textarea id="description" name="description" 
                              placeholder="İstasyon hakkında ek bilgiler"></textarea>
                </div>
                
                <button type="submit">💾 Kaydet</button>
            </form>
            
            <div class="stations-list">
                <h2>Kayıtlı İstasyonlar</h2>
                <div id="stationsContainer"></div>
            </div>
        </div>
        
        <script>
            const API_BASE = window.location.origin;
            
            function showMessage(text, type = 'success') {
                const msgEl = document.getElementById('message');
                msgEl.textContent = text;
                msgEl.className = `message ${type}`;
                msgEl.style.display = 'block';
                setTimeout(() => {
                    msgEl.style.display = 'none';
                }, 5000);
            }
            
            async function loadStations() {
                try {
                    const response = await fetch(`${API_BASE}/api/stations`);
                    const result = await response.json();
                    
                    if (result.success) {
                        displayStations(result.data);
                    }
                } catch (error) {
                    console.error('İstasyonlar yüklenemedi:', error);
                }
            }
            
            function displayStations(stations) {
                const container = document.getElementById('stationsContainer');
                
                if (stations.length === 0) {
                    container.innerHTML = '<p>Henüz kayıtlı istasyon yok.</p>';
                    return;
                }
                
                container.innerHTML = stations.map(station => `
                    <div class="station-card">
                        <h3>${station.name} (${station.station_id})</h3>
                        <p><strong>Konum:</strong> ${station.location || 'Belirtilmemiş'}</p>
                        <p><strong>Maksimum Akım:</strong> ${station.max_current_amp || 'N/A'}A</p>
                        <p><strong>Maksimum Güç:</strong> ${station.max_power_kw || 'N/A'}kW</p>
                        <p><strong>Bağlantı Tipi:</strong> ${station.connector_type || 'N/A'}</p>
                        <p><strong>Durum:</strong> ${station.status || 'active'}</p>
                        ${station.address ? `<p><strong>Adres:</strong> ${station.address}</p>` : ''}
                        ${station.description ? `<p><strong>Açıklama:</strong> ${station.description}</p>` : ''}
                        <div class="btn-group">
                            <button class="btn-edit" onclick="editStation('${station.station_id}')">✏️ Düzenle</button>
                            <button class="btn-delete" onclick="deleteStation('${station.station_id}')">🗑️ Sil</button>
                        </div>
                    </div>
                `).join('');
            }
            
            async function editStation(stationId) {
                try {
                    const response = await fetch(`${API_BASE}/api/stations/${stationId}`);
                    const result = await response.json();
                    
                    if (result.success) {
                        const station = result.data;
                        // Formu doldur
                        Object.keys(station).forEach(key => {
                            const input = document.getElementById(key);
                            if (input) {
                                input.value = station[key] || '';
                            }
                        });
                        showMessage('İstasyon bilgileri forma yüklendi. Güncellemek için Kaydet butonuna basın.', 'success');
                    }
                } catch (error) {
                    showMessage('İstasyon bilgileri yüklenemedi', 'error');
                }
            }
            
            async function deleteStation(stationId) {
                if (!confirm(`"${stationId}" istasyonunu silmek istediğinize emin misiniz?`)) {
                    return;
                }
                
                try {
                    const response = await fetch(`${API_BASE}/api/stations/${stationId}`, {
                        method: 'DELETE'
                    });
                    const result = await response.json();
                    
                    if (result.success) {
                        showMessage('İstasyon silindi', 'success');
                        loadStations();
                    } else {
                        showMessage(result.message || 'Silme işlemi başarısız', 'error');
                    }
                } catch (error) {
                    showMessage('Silme işlemi başarısız', 'error');
                }
            }
            
            document.getElementById('stationForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const data = {};
                
                formData.forEach((value, key) => {
                    if (value) {
                        // Sayısal alanları dönüştür
                        if (['max_power_kw', 'max_current_amp', 'latitude', 'longitude'].includes(key)) {
                            data[key] = parseFloat(value) || parseInt(value);
                        } else {
                            data[key] = value;
                        }
                    }
                });
                
                try {
                    // Önce mevcut istasyonu kontrol et
                    const checkResponse = await fetch(`${API_BASE}/api/stations/${data.station_id}`);
                    const checkResult = await checkResponse.json();
                    
                    let response;
                    if (checkResult.success) {
                        // Güncelle
                        response = await fetch(`${API_BASE}/api/stations/${data.station_id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(data)
                        });
                    } else {
                        // Yeni oluştur
                        response = await fetch(`${API_BASE}/api/stations`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(data)
                        });
                    }
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showMessage('İstasyon bilgileri kaydedildi!', 'success');
                        e.target.reset();
                        loadStations();
                    } else {
                        showMessage(result.message || 'Kayıt işlemi başarısız', 'error');
                    }
                } catch (error) {
                    showMessage('Kayıt işlemi başarısız: ' + error.message, 'error');
                }
            });
            
            // Sayfa yüklendiğinde istasyonları yükle
            loadStations();
        </script>
    </body>
    </html>
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

