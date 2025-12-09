# Sistem Deep Dive Analizi

**Oluşturulma Tarihi:** 2025-12-10 01:20:00
**Son Güncelleme:** 2025-12-10 01:20:00
**Version:** 1.0.0

---

## 📊 Sistem Genel Bakış

### Mimari Yapı

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Routers    │  │  Middleware  │  │   Handlers   │    │
│  │  (Modular)   │  │  (Logging)   │  │ (Exception) │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              ESP32 Bridge (Singleton)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Serial     │  │   Status     │  │   Protocol   │    │
│  │  Connection  │  │  Monitoring  │  │   Handler    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Event Detector (Threading)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Monitor    │  │   State      │  │   Event     │    │
│  │    Loop      │  │  Tracking    │  │  Callbacks  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Process Bilgileri

**API Servisi (charger-api.service):**
- **PID:** 166479
- **CPU Kullanımı:** 2.7% (Normal)
- **Memory Kullanımı:** 1.2% (49MB RSS)
- **Thread Sayısı:** 4
- **Process State:** Sleeping (Normal)
- **VM Size:** 358MB
- **VM Peak:** 423MB

**Diğer Servisler:**
- **OCPP Service:** PID 164093 (0.0% CPU, 0.2% MEM)
- **Ngrok:** PID 16898 (1.9% CPU, 0.9% MEM)
- **Wifi Monitor:** PID 976 (0.1% CPU, 0.3% MEM)

### Sistem Kaynakları

**Memory:**
- **Total:** 3.7GB
- **Used:** 1.0GB (27%)
- **Free:** 2.0GB
- **Available:** 2.7GB
- **Swap:** 2.0GB (0% kullanılıyor)

**Disk:**
- **Total:** 15GB
- **Used:** 5.9GB (44%)
- **Available:** 7.6GB

**CPU Load:**
- **1 min:** 0.46
- **5 min:** 0.60
- **15 min:** 0.57

**Uptime:** 8 saat 21 dakika

---

## 🔍 Mimari Analizi

### 1. Singleton Pattern Kullanımı

**ESP32 Bridge:**
- Singleton pattern kullanılıyor
- Thread-safe değil (potansiyel sorun)
- `get_esp32_bridge()` fonksiyonu ile erişim

**Event Detector:**
- Singleton pattern kullanılıyor
- Thread-safe (threading.Lock kullanılıyor)
- `get_event_detector()` fonksiyonu ile erişim

**Potansiyel Sorunlar:**
- ESP32 Bridge singleton'ı thread-safe değil
- Çoklu thread erişiminde race condition riski
- Startup/shutdown sırasında çakışma riski

### 2. Threading Yapısı

**Event Detector Thread:**
- Daemon thread olarak çalışıyor
- Monitor loop sürekli çalışıyor
- State değişikliklerini izliyor

**ESP32 Bridge Monitor Thread:**
- Serial port okuma thread'i
- Status mesajlarını işliyor
- Thread-safe değil (potansiyel sorun)

**Thread Sayısı:** 4 thread
- Main thread (FastAPI)
- Event detector monitor thread
- ESP32 bridge monitor thread
- Uvicorn worker thread

### 3. Bağımlılık Yönetimi

**Startup Bağımlılıkları:**
- `network-online.target` (Network hazır olmalı)
- `systemd-journald` (Logging)
- `NetworkManager-wait-online.service` (Network bağlantısı)

**Runtime Bağımlılıkları:**
- ESP32 serial port (`/dev/ttyUSB0`)
- Ngrok tunnel (dışarıdan erişim)
- File system (logs, static files)

### 4. Error Handling

**Global Exception Handler:**
- Tüm unhandled exception'ları yakalıyor
- DEBUG mode kontrolü var
- Detaylı logging yapıyor

**Potansiyel Sorunlar:**
- Startup/shutdown hataları loglanıyor ama servis çökebilir
- Serial port hataları yakalanıyor ama recovery mekanizması yok
- Event callback hataları yakalanıyor ama callback listesi temizlenmiyor

---

## 🐛 Tespit Edilen Sorunlar

### 1. Thread Safety Sorunları

**ESP32 Bridge:**
- Singleton pattern thread-safe değil
- `status_lock` var ama `_instance` kontrolü yok
- Çoklu thread erişiminde race condition riski

**Öneri:**
```python
import threading

_instance = None
_instance_lock = threading.Lock()

def get_esp32_bridge():
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ESP32Bridge()
    return _instance
```

### 2. Serial Port Hataları

**Tespit Edilen Hatalar:**
- "device reports readiness to read but returned no data"
- "device disconnected or multiple access on port"
- Mock object hataları (test ortamından kalmış)

**Nedenler:**
- ESP32 bağlantısı kopmuş olabilir
- Çoklu process erişimi olabilir
- Serial port buffer sorunları

**Öneri:**
- Serial port erişimini kontrol et
- Reconnection mekanizması ekle
- Port locking mekanizması ekle

### 3. Startup/Shutdown Hataları

**Tespit Edilen Hatalar:**
- Startup hatası: Mock object hatası (test ortamından)
- Shutdown hatası: Mock object hatası (test ortamından)
- ESP32 bağlantısı başlatılamadı uyarıları

**Nedenler:**
- Test mock'ları production kodunda kalmış
- ESP32 bağlantısı başlatılamamış
- Graceful shutdown mekanizması eksik

**Öneri:**
- Test mock'larını temizle
- Startup/shutdown hatalarını daha iyi handle et
- Graceful shutdown mekanizması ekle

### 4. Event Callback Hataları

**Tespit Edilen Hatalar:**
- Callback error: "Callback error"
- Callback listesi temizlenmiyor
- Hatalı callback'ler tekrar çağrılıyor

**Nedenler:**
- Callback'ler exception fırlatıyor
- Callback listesi temizlenmiyor
- Error handling eksik

**Öneri:**
- Callback hatalarını yakala ve logla
- Hatalı callback'leri listeden çıkar
- Callback timeout mekanizması ekle

---

## 📈 Performans Analizi

### API Response Times

**Normal İstekler:**
- `/api/health`: ~3-5ms
- `/api/status`: ~3-5ms
- `/api/test/key`: ~1-2ms

**Performans Metrikleri:**
- Ortalama response time: 3-5ms (Çok iyi)
- CPU kullanımı: 2.7% (Düşük)
- Memory kullanımı: 49MB (Düşük)
- Thread sayısı: 4 (Normal)

### Kaynak Kullanımı

**Memory:**
- API Servisi: 49MB (1.2%)
- Toplam Sistem: 1.0GB (27%)
- Available: 2.7GB (73%)

**CPU:**
- API Servisi: 2.7%
- Toplam Sistem: ~5%
- Load Average: 0.46-0.60

**Disk:**
- Kullanım: 5.9GB / 15GB (44%)
- Log dosyaları: ~20MB
- Available: 7.6GB

---

## 🔒 Güvenlik Analizi

### Port Erişimi

**Açık Portlar:**
- **8000:** API servisi (0.0.0.0:8000 - Tüm ağlardan erişilebilir)
- **4040:** Ngrok (127.0.0.1:4040 - Sadece localhost)
- **22:** SSH (0.0.0.0:22 - Tüm ağlardan erişilebilir)

**Güvenlik Önerileri:**
- API servisi firewall ile korunmalı
- SSH key-based authentication kullanılmalı
- API authentication aktif (✅)

### Authentication

**API Authentication:**
- X-API-Key header kullanılıyor
- SECRET_API_KEY environment variable'dan alınıyor
- Test endpoint'i production'da devre dışı (✅)

### Logging

**Log Güvenliği:**
- API istekleri loglanıyor
- Client IP loglanıyor
- User ID loglanıyor (audit trail)
- Sensitive data loglanmıyor (✅)

---

## 🚨 Risk Analizi

### Yüksek Risk

1. **Thread Safety Sorunları:**
   - ESP32 Bridge singleton thread-safe değil
   - Race condition riski
   - **Etki:** Veri kaybı, servis çökmesi

2. **Serial Port Hataları:**
   - Reconnection mekanizması yok
   - Port locking yok
   - **Etki:** ESP32 iletişim kesintisi

### Orta Risk

1. **Startup/Shutdown Hataları:**
   - Graceful shutdown eksik
   - Error recovery mekanizması yok
   - **Etki:** Servis başlatma/kapama sorunları

2. **Event Callback Hataları:**
   - Hatalı callback'ler temizlenmiyor
   - Callback timeout yok
   - **Etki:** Event detection sorunları

### Düşük Risk

1. **Memory Leaks:**
   - Şu an için tespit edilmedi
   - Monitoring gerekli
   - **Etki:** Uzun vadede performans sorunları

2. **Disk Kullanımı:**
   - Log rotation aktif değil
   - Disk dolabilir
   - **Etki:** Log kaybı, disk dolması

---

## 💡 İyileştirme Önerileri

### 1. Thread Safety İyileştirmeleri

**ESP32 Bridge Singleton:**
```python
import threading

_instance = None
_instance_lock = threading.Lock()

def get_esp32_bridge():
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ESP32Bridge()
    return _instance
```

**Avantajlar:**
- Thread-safe singleton
- Race condition önlendi
- Çoklu thread erişimi güvenli

### 2. Serial Port Reconnection

**Reconnection Mekanizması:**
```python
def reconnect(self, max_retries=3, retry_delay=5):
    for i in range(max_retries):
        try:
            if self.connect():
                return True
        except Exception as e:
            logger.warning(f"Reconnection attempt {i+1} failed: {e}")
            time.sleep(retry_delay)
    return False
```

**Avantajlar:**
- Otomatik reconnection
- ESP32 bağlantı kesintilerinde recovery
- Daha güvenilir iletişim

### 3. Graceful Shutdown

**Shutdown Mekanizması:**
```python
@app.on_event("shutdown")
async def shutdown_event():
    try:
        # Event detector'ı durdur
        event_detector.stop_monitoring()
        # Thread'lerin bitmesini bekle
        if event_detector._monitor_thread:
            event_detector._monitor_thread.join(timeout=5)
        # ESP32 bridge'i kapat
        bridge.disconnect()
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
```

**Avantajlar:**
- Temiz kapanma
- Thread'lerin düzgün bitmesi
- Kaynak temizliği

### 4. Health Check İyileştirmeleri

**Detaylı Health Check:**
```python
@app.get("/api/health")
async def health_check():
    health = {
        "api": "healthy",
        "esp32_connected": bridge.is_connected,
        "event_detector": event_detector.is_monitoring,
        "threads": threading.active_count(),
        "memory": psutil.Process().memory_info().rss / 1024 / 1024
    }
    return health
```

**Avantajlar:**
- Detaylı sistem durumu
- Monitoring için kullanılabilir
- Sorun tespiti kolaylaşır

### 5. Log Rotation

**Log Rotation Yapılandırması:**
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'logs/api.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

**Avantajlar:**
- Disk kullanımı kontrol altında
- Eski loglar arşivlenir
- Disk dolması önlenir

---

## 📊 Monitoring Önerileri

### 1. Metrik Toplama

**Toplanacak Metrikler:**
- API response times
- Error rates
- Memory usage
- CPU usage
- Thread count
- ESP32 connection status
- Event detection rate

### 2. Alerting

**Alert Koşulları:**
- API response time > 100ms
- Error rate > 5%
- Memory usage > 80%
- CPU usage > 80%
- ESP32 disconnected > 30s
- Thread count > 10

### 3. Dashboard

**Dashboard Metrikleri:**
- Real-time system status
- API performance metrics
- Error rates
- Resource usage
- ESP32 connection status

---

## 🎯 Sonuç ve Öncelikler

### Kritik Öncelik

1. **Thread Safety İyileştirmeleri** (Yüksek Risk)
   - ESP32 Bridge singleton thread-safe yapılmalı
   - Race condition riski ortadan kaldırılmalı

2. **Serial Port Reconnection** (Yüksek Risk)
   - Reconnection mekanizması eklenmeli
   - Port locking mekanizması eklenmeli

### Orta Öncelik

3. **Graceful Shutdown** (Orta Risk)
   - Shutdown mekanizması iyileştirilmeli
   - Thread'lerin düzgün bitmesi sağlanmalı

4. **Event Callback İyileştirmeleri** (Orta Risk)
   - Hatalı callback'ler temizlenmeli
   - Callback timeout mekanizması eklenmeli

### Düşük Öncelik

5. **Log Rotation** (Düşük Risk)
   - Log rotation yapılandırılmalı
   - Disk kullanımı kontrol altına alınmalı

6. **Monitoring İyileştirmeleri** (Düşük Risk)
   - Metrik toplama eklenmeli
   - Alerting mekanizması eklenmeli

---

## 📝 Notlar

- Sistem genel olarak sağlıklı çalışıyor
- Performans metrikleri iyi
- Kaynak kullanımı düşük
- Thread safety sorunları kritik
- Serial port hataları dikkat gerektiriyor
- Monitoring ve alerting eksik

---

## 🔗 İlgili Dokümantasyon

- **Servis Çökme Analizi:** `docs/SERVICE_CRASH_ANALYSIS.md`
- **Servis Migrasyon Rehberi:** `docs/SERVICE_MIGRATION_GUIDE.md`
- **Troubleshooting:** `docs/troubleshooting.md`

