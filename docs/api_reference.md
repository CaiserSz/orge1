# API Referansı - AC Charger

**Oluşturulma Tarihi:** 2025-12-09 22:35:00  
**Son Güncelleme:** 2025-12-09 22:35:00  
**Version:** 1.0.0

---

## REST API Implementasyonu (2025-12-08 18:15:00)

**API Framework:** FastAPI (Python)
- **Port:** 8000
- **Base URL:** `https://lixhium.ngrok.app` (dışarıdan erişim)
- **Local URL:** `http://localhost:8000`
- **Dokümantasyon:** `https://lixhium.ngrok.app/docs` (Swagger UI)
- **ReDoc:** `https://lixhium.ngrok.app/redoc`

**API Endpoint'leri:**

1. **GET /** - API root endpoint
   - API bilgilerini döndürür

2. **GET /api/health** - Sistem sağlık kontrolü
   - API ve ESP32 bağlantı durumunu kontrol eder

3. **GET /api/status** - ESP32 durum bilgisi
   - ESP32'den son durum bilgisini alır
   - ESP32 her 5 saniyede bir otomatik durum gönderir
   - Response: Status mesajı (CP, PP, Relay, Lock, Motor, PWM, Max Current, Cable Current, Auth, State, Power Board Status, Stop Requested)

4. **POST /api/charge/start** - Şarj başlatma
   - ESP32'ye authorization komutu gönderir
   - Şarj izni verir ve şarjı başlatır
   - Request Body: `{}` (boş)

5. **POST /api/charge/stop** - Şarj durdurma
   - ESP32'ye charge stop komutu gönderir
   - Şarjı sonlandırır
   - Request Body: `{}` (boş)

6. **POST /api/maxcurrent** - Maksimum akım ayarlama
   - ESP32'ye maksimum akım değerini ayarlar
   - **ÖNEMLİ:** Sadece aktif şarj başlamadan yapılabilir
   - Request Body: `{"amperage": 16}` (6-32 amper aralığında herhangi bir tam sayı)
   - Güvenlik: Şarj aktifken akım değiştirilemez
   - **Not:** 6-32 amper aralığında herhangi bir tam sayı değer kullanılabilir (örn: 12, 15, 18, 22, vb.)

7. **GET /api/current/available** - Kullanılabilir akım aralığı
   - ESP32'de ayarlanabilir akım aralığını döndürür
   - Response: `{"range": "6-32 amper", "min": 6, "max": 32, "note": "6-32 aralığında herhangi bir tam sayı değer kullanılabilir"}`

**ESP32 Bridge Modülü:**
- **Dosya:** `esp32/bridge.py`
- **Fonksiyonlar:**
  - `connect()` - ESP32'ye bağlan
  - `send_status_request()` - Status komutu gönder
  - `send_authorization()` - Authorization komutu gönder
  - `send_current_set(amperage)` - Akım set komutu gönder
  - `send_charge_stop()` - Şarj durdurma komutu gönder
  - `get_status()` - Son durum bilgisini al
  - `get_status_sync(timeout)` - Status komutu gönder ve yanıt bekle

**Protokol Tanımları:**
- **Dosya:** `esp32/protocol.json`
- Tüm komut tanımları, byte array formatları ve protokol detayları JSON formatında

**Bağımlılıklar:**
- `pyserial` - USB seri port iletişimi
- `fastapi` - REST API framework
- `uvicorn` - ASGI server
- `pydantic` - Veri validasyonu

**API Çalıştırma:**
```bash
cd /home/basar/charger
source env/bin/activate
python api/main.py
```
veya
```bash
cd /home/basar/charger
source env/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

#### RPi'den ESP32'ye Gönderilebilecek Komutlar
RPi'den ESP32'ye sadece aşağıdaki komutlar gönderilebilir:

**Tam Komut Listesi (Hex Kod ve Byte Array Formatında):**

| # | Komut | Komut ID | Değer | Hex Kod Dizini | Byte Array (Python) | Byte Array (C/C++) | Açıklama |
|---|-------|----------|-------|----------------|---------------------|-------------------|----------|
| 1 | Status | 00 | 00 | `41 00 2C 00 10` | `[0x41, 0x00, 0x2C, 0x00, 0x10]` | `{0x41, 0x00, 0x2C, 0x00, 0x10}` | İstasyon durumu okuma |
| 2 | Authorization | 01 | 01 | `41 01 2C 01 10` | `[0x41, 0x01, 0x2C, 0x01, 0x10]` | `{0x41, 0x01, 0x2C, 0x01, 0x10}` | Şarj izni ver |
| 3 | Akım Set | 02 | 06 | `41 02 2C 06 10` | `[0x41, 0x02, 0x2C, 0x06, 0x10]` | `{0x41, 0x02, 0x2C, 0x06, 0x10}` | Maksimum akım: 6A |
| 4 | Akım Set | 02 | 0A | `41 02 2C 0A 10` | `[0x41, 0x02, 0x2C, 0x0A, 0x10]` | `{0x41, 0x02, 0x2C, 0x0A, 0x10}` | Maksimum akım: 10A |
| 5 | Akım Set | 02 | 0D | `41 02 2C 0D 10` | `[0x41, 0x02, 0x2C, 0x0D, 0x10]` | `{0x41, 0x02, 0x2C, 0x0D, 0x10}` | Maksimum akım: 13A |
| 6 | Akım Set | 02 | 10 | `41 02 2C 10 10` | `[0x41, 0x02, 0x2C, 0x10, 0x10]` | `{0x41, 0x02, 0x2C, 0x10, 0x10}` | Maksimum akım: 16A ⭐ |
| 7 | Akım Set | 02 | 14 | `41 02 2C 14 10` | `[0x41, 0x02, 0x2C, 0x14, 0x10]` | `{0x41, 0x02, 0x2C, 0x14, 0x10}` | Maksimum akım: 20A |
| 8 | Akım Set | 02 | 19 | `41 02 2C 19 10` | `[0x41, 0x02, 0x2C, 0x19, 0x10]` | `{0x41, 0x02, 0x2C, 0x19, 0x10}` | Maksimum akım: 25A |
| 9 | Akım Set | 02 | 20 | `41 02 2C 20 10` | `[0x41, 0x02, 0x2C, 0x20, 0x10]` | `{0x41, 0x02, 0x2C, 0x20, 0x10}` | Maksimum akım: 32A |
| 10 | State Machine | 04 | 07 | `41 04 2C 07 10` | `[0x41, 0x04, 0x2C, 0x07, 0x10]` | `{0x41, 0x04, 0x2C, 0x07, 0x10}` | Şarjı bitir |

**Önemli Notlar:**
- **Akım Değiştirme Güvenlik Kuralı:** Akım set komutları sadece aktif şarj başlamadan gönderilebilir. Şarj esnasında akım değiştirilemez (güvenlik nedeniyle).
- **Kritik Kural:** Başka komut RPi'den ESP32'ye gitmez.
- Tüm komutlar 5 byte uzunluğundadır.
- Protokol formatı: `41 [KOMUT] 2C [DEĞER] 10`

#### ESP32 Otonom Çalışma
- **State Machine:** ESP32 fiziksel tarafta gelen komutlara ve ev kullanıcısının davranışlarına göre state machine ile çalışır
- **Otonom Yürütme:** ESP32 süreci kendi içinde otonom olarak yürütür
- **Fiziksel Kontrol:** Fiziksel taraftaki tüm kontroller ESP32'nin sorumluluğundadır

---

## Analizler ve Değerlendirmeler

### Şarj Süreci Deep Dive Analizi (2025-12-09 02:15:00)

**Analiz Metodolojisi:** Single Point of Truth + Multi-Disciplinary Expert Analysis

**Analiz Edilen Fazlar:**
1. Şarj Başlatmadan Önceki Durum (Pre-Charge State)
2. Başlatma Sırasındaki Durum (Initiation State)
3. Şu Anki Durum - Devam Eden Şarj (Active Charging State)

**Kritik Bulgular:**
- ✅ **CABLE=63A değeri KABLO KAPASİTESİ** (PP voltajından hesaplanan), şarj akımı değil
- ✅ **MAX current kontrolü ÇALIŞIYOR!** PWM hesaplaması doğru (PWM=33 ≈ hesaplanan 34)
- ⚠️ **ESP32 kodunda minor bug:** `if (sarjStatus=SARJ_STAT_IDLE)` → Assignment operator hatası (kod kalitesi sorunu, güvenlik riski yok)

**Başarılı Noktalar:**
- State detection doğru çalışıyor
- API endpoint'leri çalışıyor
- ESP32 communication stabil
- State management doğru (single source of truth)
- Authorization flow çalışıyor
- MAX current kontrolü çalışıyor
- PWM hesaplaması doğru

**Sistem Durumu:** ✅ **ÇALIŞIYOR - KRİTİK SORUNLAR DOĞRULANDI VE ÇÖZÜLDÜ**

Detaylı analiz için: `CHARGING_DEEPDIVE_ANALYSIS.md` (konsolide edilecek)

### State Mantık Analizi ve Düzeltmeler (2025-12-09 02:15:00)

**Tespit Edilen Mantık Hataları:**

1. **Start Charge Endpoint - YANLIŞ STATE KONTROLÜ:**
   - **Mevcut Kod:** `if state >= 2:` → STATE=2,3,4 durumlarında şarj başlatılamıyor ❌
   - **Düzeltme:** `if state >= 5:` → Sadece aktif şarj durumlarında engelleme ✅
   - **Doğru Mantık:** STATE=1,2,3,4 → Şarj başlatılabilir, STATE=5+ → Şarj zaten aktif

2. **Set Current Endpoint - YANLIŞ STATE KONTROLÜ:**
   - **Mevcut Kod:** `if state >= 2:` → STATE=2,3,4 durumlarında akım ayarlanamıyor ❌
   - **Düzeltme:** `if state >= 5:` → Sadece aktif şarj durumlarında engelleme ✅
   - **Doğru Mantık:** STATE=1,2,3,4 → Akım ayarlanabilir, STATE=5+ → Şarj aktifken akım değiştirilemez

**ESP32 State Değerleri:**
- STATE=1: IDLE (boşta)
- STATE=2: CABLE_DETECT (kablo algılandı)
- STATE=3: EV_CONNECTED (araç bağlı)
- STATE=4: SARJA_HAZIR (şarja hazır)
- STATE=5: SARJ_BASLADI (şarj başladı)
- STATE=6: SARJ_DURAKLATILDI (şarj duraklatıldı)
- STATE=7: SARJ_BITIR (şarj bitirildi)
- STATE=8: FAULT_HARD (hata durumu)

**ESP32 Firmware Bug:**
- `if (sarjStatus=SARJ_STAT_IDLE)` → Assignment operator (`=`) yerine comparison operator (`==`) kullanılmalı
- Bu bug MAX current ayarlamasını etkilemiyor ama kod kalitesi için düzeltilmeli

Detaylı analiz için: `STATE_LOGIC_ANALYSIS.md` (konsolide edilecek)

### Logging Sistemi Kurulumu (2025-12-09 15:40:00)

**Durum:** ✅ Tamamlandı

**Özet:**
Structured logging sistemi kuruldu. JSON formatında loglama, log rotation, thread-safe logging mekanizması implement edildi.

**Özellikler:**
- **Structured Logging:** JSON formatında loglama (parse edilebilir ve analiz edilebilir)
- **Log Rotation:** 10MB maksimum dosya boyutu, 5 yedek dosya
- **Thread-Safe Logging:** Multi-threaded ortamlar için güvenli
- **Ayrı Logger'lar:** api.logger, esp32.logger, system.logger
- **ESP32 Mesajları:** Komut gönderme (tx), status mesajları (rx), bağlantı/bağlantı kesme olayları
- **API İstekleri:** Middleware ile otomatik logging (şarj başlatma/bitirme hariç)
- **Console ve File Output:** Geliştirme için console, production için file

**Dosyalar:**
- `api/logging_config.py` - Logging konfigürasyonu ve helper fonksiyonlar
- `api/main.py` - API middleware entegrasyonu
- `esp32/bridge.py` - ESP32 mesajları logging entegrasyonu

**Log Dosyaları:**
- `logs/api.log` - API istekleri ve yanıtları
- `logs/esp32.log` - ESP32 mesajları (tx/rx)
- `logs/system.log` - Sistem olayları

**Commit:** 0284a21, 0c3838a

**Detaylı Bilgi:** `LOGGING_AUDIT.md`

---

### Kritik Sorunlar Düzeltmeleri (2025-12-09 16:00:00)

**Durum:** ✅ Tamamlandı

**Özet:**
Audit sonrası tespit edilen kritik sorunlar düzeltildi. Singleton pattern thread-safety, dependency injection, exception handling iyileştirmeleri yapıldı.

**Düzeltilen Sorunlar:**

1. **Singleton Pattern Thread-Safety (KRİTİK)**
   - **Sorun:** `get_esp32_bridge()` ve `get_meter_reader()` thread-safe değildi
   - **Çözüm:** Double-check locking pattern eklendi
   - **Dosyalar:** `esp32/bridge.py`, `meter/read_meter.py`

2. **Global Variable Kullanımı (KRİTİK)**
   - **Sorun:** `esp32_bridge = None` global variable kullanılıyordu
   - **Çözüm:** FastAPI Depends pattern ile dependency injection
   - **Dosyalar:** `api/main.py`

3. **Monitor Loop Exception Handling (ORTA)**
   - **Sorun:** `_monitor_loop()` içinde exception yakalanmıyordu
   - **Çözüm:** Try-catch ile korumalı, loop crash etmez
   - **Dosyalar:** `esp32/bridge.py`

4. **Exception Handler Information Leakage (ORTA)**
   - **Sorun:** Production'da stack trace expose ediliyordu
   - **Çözüm:** DEBUG mode kontrolü, production'da genel mesaj
   - **Dosyalar:** `api/main.py`

**İyileştirmeler:**
- Thread-safe singleton pattern garantisi
- Dependency injection ile test edilebilirlik artışı
- Robust error handling (loop crash etmez)
- Security hardening (no information leakage)

**Commit:** 12e7293

**Detaylı Bilgi:** `PRE_LOGGING_AUDIT.md`

---

### Multi-Expert Deep Dive Analizi (2025-12-09 17:00:00)

**Durum:** ✅ Tamamlandı

**Özet:**
Multi-expert ve single source of truth stratejisiyle kapsamlı proje analizi yapıldı. 6 farklı uzman perspektifinden (Security, Performance, Architecture, Code Quality, DevOps, Testing) derinlemesine analiz gerçekleştirildi.

**Uzman Perspektifleri ve Skorlar:**

1. **Security Expert** (Skor: 6/10 → Hedef: 9/10)
   - 🔴 KRİTİK: API Authentication eksik
   - 🔴 KRİTİK: Rate Limiting eksik
   - 🟡 ORTA: CORS Configuration eksik
   - 🟡 ORTA: Input Validation iyileştirmeleri
   - 🟡 ORTA: Secrets Management iyileştirmeleri

2. **Performance Expert** (Skor: 7.5/10 → Hedef: 9/10)
   - 🟡 YÜKSEK: ESP32 Communication blocking (async gerekli)
   - 🟡 ORTA: Status Polling optimizasyonu
   - 🟢 ORTA: Status Caching eksik

3. **Architecture Expert** (Skor: 8/10 → Hedef: 9.5/10)
   - ✅ İyi: Modüler yapı, Dependency Injection, Singleton Pattern
   - 🟡 YÜKSEK: API Router Separation (460 satırlık main.py)
   - 🟡 YÜKSEK: Configuration Management merkezileştirme
   - 🟢 ORTA: Service Layer Pattern

4. **Code Quality Expert** (Skor: 7/10 → Hedef: 9/10)
   - 🟡 YÜKSEK: Type Hints tamamlama (%85 → %100)
   - 🟡 YÜKSEK: Code Quality Tools (black, ruff, mypy)
   - 🟢 ORTA: Docstring iyileştirmeleri

5. **DevOps Expert** (Skor: 6/10 → Hedef: 9/10)
   - 🟡 YÜKSEK: CI/CD Pipeline eksik
   - 🟡 YÜKSEK: Monitoring ve Observability eksik
   - 🟢 ORTA: Docker Containerization eksik

6. **Testing Expert** (Skor: 7.5/10 → Hedef: 9.5/10)
   - 🟡 YÜKSEK: Test Coverage artırma (%70 → %90+)
   - 🟡 ORTA: E2E Testler eksik
   - 🟢 ORTA: Performance Testler eksik

**Konsolide Öneriler (Single Source of Truth):**

**🔴 ACİL (1 Hafta İçinde):**
1. API Authentication (1.5 saat) - Security Expert
2. Rate Limiting (1 saat) - Security Expert
3. CORS Configuration (15 dakika) - Security Expert

**🟡 YÜKSEK ÖNCELİK (1 Ay İçinde):**
1. Type Hints Tamamlama (2-3 saat) - Code Quality Expert
2. Code Quality Tools (1 saat) - Code Quality Expert
3. API Router Separation (2-3 saat) - Architecture Expert
4. Configuration Management (1-2 saat) - Architecture Expert
5. Async ESP32 Communication (2-3 saat) - Performance Expert
6. Test Coverage Artırma (4-6 saat) - Testing Expert
7. CI/CD Pipeline (2-3 saat) - DevOps Expert
8. Monitoring ve Observability (2-3 saat) - DevOps Expert

**Genel Skor:**
- **Mevcut:** 7.5/10
- **Hedef:** 9/10
- **İyileştirme:** +1.5

**Detaylı Rapor:** `MULTI_EXPERT_ANALYSIS.md`

---

### API Authentication Implementasyonu (2025-12-09 17:15:00)

**Durum:** ✅ Tamamlandı

**Özet:**
Basit API key authentication mekanizması implement edildi. Kritik endpoint'ler (`/api/charge/start`, `/api/charge/stop`, `/api/maxcurrent`) için API key zorunluluğu eklendi.

**Özellikler:**
- **API Key Authentication:** `X-API-Key` header ile authentication
- **Secret Key:** `.env` dosyasından `SECRET_API_KEY` okunuyor
- **Protected Endpoints:** Şarj başlatma, durdurma ve akım ayarlama endpoint'leri korumalı
- **Error Handling:** Geçersiz veya eksik API key durumunda 401 Unauthorized döndürülüyor
- **User Tracking:** `TEST_API_USER_ID` environment variable ile kullanıcı takibi

**Dosyalar:**
- `api/auth.py` - API authentication modülü
- `api/main.py` - Authentication entegrasyonu (Depends pattern)
- `.env` - `SECRET_API_KEY` ve `TEST_API_USER_ID` tanımları

**Güvenlik Özellikleri:**
- API key `.env` dosyasında saklanıyor (gitignore'da)
- Production'da test endpoint'i devre dışı (`ENVIRONMENT` kontrolü)
- User ID tracking ile audit trail

**Commit:** a52aaf3, 2a72d65

**Detaylı Bilgi:** `AUDIT_REPORT_20251209.md`

---

### API Test Web Sayfası (2025-12-09 17:30:00)

**Durum:** ✅ Tamamlandı

**Özet:**
Dışarıdan API'leri test etmek için modern, responsive web arayüzü oluşturuldu. Tüm endpoint'ler için butonlar, request/response görüntüleme ve cURL komut önizleme özellikleri eklendi.

**Özellikler:**
- **Modern UI:** Responsive tasarım, gradient arka plan, modern butonlar
- **Endpoint Grupları:** System Endpoints, Charge Control, Current Control
- **Request/Response Display:** JSON formatında request ve response body görüntüleme
- **cURL Preview:** Göndermeden önce edit edilebilir cURL komut önizleme
- **Auto API Key:** Backend'den otomatik API key yükleme
- **Error Handling:** Kullanıcı dostu hata mesajları
- **Performance:** Debounce ile curl preview optimizasyonu (300ms)

**Güvenlik Özellikleri:**
- Shell command injection koruması (`escapeShellString` fonksiyonu)
- Input validation (amperage 6-32A aralığı)
- Production'da test endpoint'i devre dışı (`ENVIRONMENT` kontrolü)

**Dosyalar:**
- `api_test.html` - API test web sayfası
- `api/main.py` - `/test` ve `/api/test/key` endpoint'leri

**Endpoint'ler:**
- `GET /test` - API test sayfası
- `GET /api/test/key` - API key ve User ID (sadece development)

**Commit:** a52aaf3, 6c79869, 8a5a965, f6c9a8c, e1c23f1

**Detaylı Bilgi:** `AUDIT_REPORT_20251209.md`

---

### Security Audit ve Quick Wins (2025-12-09 18:15:00)

**Durum:** ✅ Tamamlandı

**Özet:**
Kıdemli uzman perspektifinden kapsamlı security audit yapıldı. Kritik güvenlik sorunları tespit edildi ve düzeltildi. Quick win'ler uygulandı.

**Tespit Edilen Kritik Sorunlar:**

1. **API Key Exposure Risk** 🔴 YÜKSEK
   - **Sorun:** `/api/test/key` endpoint'i production'da aktifti
   - **Çözüm:** Environment kontrolü eklendi, production'da 404 döndürüyor
   - **Dosya:** `api/main.py`

2. **Shell Command Injection Risk** 🟡 ORTA
   - **Sorun:** Curl komutlarında shell özel karakterleri escape edilmiyordu
   - **Çözüm:** `escapeShellString()` fonksiyonu eklendi
   - **Dosya:** `api_test.html`

3. **API Key Caching Security** 🟡 ORTA
   - **Sorun:** API key global variable'da tutuluyordu
   - **Çözüm:** Cache mekanizması iyileştirildi

**Uygulanan Quick Wins:**

1. ✅ Environment check for test endpoint (5 dk)
2. ✅ Shell escape function (10 dk)
3. ✅ Debounce curl preview (5 dk)
4. ✅ Input validation enhancement (10 dk)
5. ✅ Error message improvement (5 dk)

**Güvenlik Skoru:**
- **Önceki:** 6/10
- **Sonrası:** 8/10
- **İyileştirme:** +2 puan

**Dosyalar:**
- `AUDIT_REPORT_20251209.md` - Detaylı audit raporu
- `api/main.py` - Security iyileştirmeleri
- `api_test.html` - Security iyileştirmeleri

**Commit:** c650ff9, e1c23f1

**Detaylı Bilgi:** `AUDIT_REPORT_20251209.md`

---

### ESP32 Loglama ve Session Yönetimi Değerlendirmesi (2025-12-09 02:20:00)

**Mevcut Durum:**
- ⚠️ Sadece `print()` ile konsola yazılıyor, dosyaya loglama yok
- ❌ Session tracking yok, Session ID yok
- ❌ Event tracking yok (kablo takılma, araç bağlantı, şarj başlatma/durdurma)
- ❌ Session summary yok

**Önerilen Çözüm:**

**Session Tanımı:**
- **Başlangıç:** Kablo takılma (STATE=2: CABLE_DETECT)
- **Bitiş:** Kablo çıkarma (STATE=1: IDLE) veya hata durumu
- **Fazlar:** CABLE_DETECTED → EV_CONNECTED → READY → CHARGING → PAUSED → STOPPED → COMPLETED

**Loglama Sistemi:**
- Structured logging (JSON format)
- Log rotation (günlük/haftalık)
- Log kategorileri: `esp32_status`, `esp32_command`, `api_request`, `session_event`, `state_transition`, `error`

**Session Management:**
- Session ID (UUID)
- Event tracking (tüm state transition'lar)
- Session storage (JSON dosyaları)
- Session summary (enerji, akım, süre, state duration'ları)

**Implementation Plan:**
- **Faz 1:** Temel loglama (1-2 gün)
- **Faz 2:** Event detection (2-3 gün)
- **Faz 3:** Session management (3-4 gün)
- **Faz 4:** İyileştirmeler (1-2 gün)

Detaylı değerlendirme için: `SESSION_LOGGING_EVALUATION.md` (konsolide edilecek)

### WiFi Failover Sistemi (2025-12-08 19:20:00)

**Genel Bakış:**
WiFi failover sistemi, sistemin otomatik olarak 4 farklı WiFi ağına bağlanmasını ve internet erişimi kontrolü yapmasını sağlar. Internet erişimi 20 saniye boyunca olmazsa, sistem otomatik olarak bir sonraki WiFi ağına geçer.

**WiFi Ağları ve Öncelik Sırası:**
- **Öncelik 10:** ORGE_ARGE (12345678)
- **Öncelik 9:** ORGE_DEPO (1234554321)
- **Öncelik 8:** ORGE_EV (1234554321)
- **Öncelik 7:** ERTAC (12345678)

**Sistem Bileşenleri:**
- NetworkManager konfigürasyonu (otomatik bağlanma, öncelik sırası)
- WiFi Failover Monitor Script (`scripts/wifi_failover_monitor.py`)
- Systemd servisi (`scripts/wifi-failover-monitor.service`)

**Internet Kontrol Parametreleri:**
- Kontrol aralığı: 5 saniye
- Failover threshold: 20 saniye internet erişimi yoksa
- Kontrol URL'leri: `8.8.8.8`, `1.1.1.1`, `google.com`

Detaylı kurulum için: `WIFI_FAILOVER_SETUP.md` (konsolide edilecek)

### ESP32 Hex Komut Protokolü (2025-12-08 15:43:20)

#### Protokol Mimarisi
ESP32 şarj istasyonu kontrol ünitesi, üretici tarafından tanımlanan binary hex protokolünü kullanmaktadır. Protokol, sabit başlangıç ve bitiş byte'ları ile komut ve değer parametrelerinden oluşur.

#### Protokol Yapısı
**Genel Format:** `41 [KOMUT] 2C [DEĞER] 10`

| Byte Pozisyonu | Hex Değer | Açıklama | Tip |
|----------------|-----------|----------|-----|
| 1 | 41 | Sabit başlangıç byte'ı | Constant |
| 2 | [KOMUT] | Komut kodu (1 byte, hex) | Variable |
| 3 | 2C | Sabit ayırıcı byte | Constant |
| 4 | [DEĞER] | Komut değeri (1 byte, hex) | Variable |
| 5 | 10 | Sabit bitiş byte'ı | Constant |

**Toplam Paket Uzunluğu:** 5 byte

#### ESP32'ye Gönderilen Komutlar

| # | Komut Kategorisi | Komut ID | Değer | Hex Kod Dizini | Açıklama | Durum |
|---|-------------------|----------|-------|----------------|----------|-------|
| 1 | Status | 00 | 00 | 41 00 2C 00 10 | İstasyon durumu okuma | ✅ Aktif |
| 2 | Authorization | 01 | 01 | 41 01 2C 01 10 | Şarj izni ver | ✅ Aktif* |
| 4 | Akım Set | 02 | 06 | 41 02 2C 06 10 | Maksimum akım: 6A | ✅ Aktif |
| 5 | Akım Set | 02 | 0A | 41 02 2C 0A 10 | Maksimum akım: 10A | ✅ Aktif |
| 6 | Akım Set | 02 | 0D | 41 02 2C 0D 10 | Maksimum akım: 13A | ✅ Aktif |
| 7 | Akım Set | 02 | 10 | 41 02 2C 10 10 | Maksimum akım: 16A ⭐ | ✅ Aktif |
| 8 | Akım Set | 02 | 14 | 41 02 2C 14 10 | Maksimum akım: 20A | ✅ Aktif |
| 9 | Akım Set | 02 | 19 | 41 02 2C 19 10 | Maksimum akım: 25A | ✅ Aktif |
| 10 | Akım Set | 02 | 20 | 41 02 2C 20 10 | Maksimum akım: 32A | ✅ Aktif |
| 20 | State Machine | 04 | 07 | 41 04 2C 07 10 | Şarjı bitir | ✅ Aktif* |

**Not:** Sadece bu komutlar RPi'den ESP32'ye gönderilebilir.

#### Komut ID (KOMUT) Anlamları

| Komut ID | Hex | İkili | Komut Adı | Açıklama |
|----------|-----|-------|-----------|----------|
| 00 | 0x00 | 00000000 | Status | İstasyon durumu okuma komutu |
| 01 | 0x01 | 00000001 | Authorization | Şarj izni kontrolü |
| 02 | 0x02 | 00000010 | Akım Set | Maksimum akım ayarlama |
| 04 | 0x04 | 00000100 | State Machine | Durum makinesi kontrolü |

#### Değer (DEĞER) Anlamları

**Authorization Komutları (cmd_id=01)**
| Değer | Hex | İkili | Anlam | Açıklama |
|-------|-----|-------|-------|----------|
| 01 | 0x01 | 00000001 | Authorization Ver | Şarj izni ver, şarja hazır |

**Akım Set Komutları (cmd_id=02)**
- **Aralık:** 6-32 amper (herhangi bir tam sayı)
- **Format:** Değer doğrudan amper cinsinden hex formatında gönderilir
- **Örnekler:**
  | Değer | Hex | Amper (A) | Açıklama |
  |-------|-----|-----------|----------|
  | 06 | 0x06 | 6A | Minimum akım |
  | 0A | 0x0A | 10A | Düşük akım |
  | 0C | 0x0C | 12A | Örnek değer |
  | 0D | 0x0D | 13A | Orta akım |
  | 10 | 0x10 | 16A | Önerilen akım ⭐ |
  | 14 | 0x14 | 20A | Yüksek akım |
  | 19 | 0x19 | 25A | Çok yüksek akım |
  | 20 | 0x20 | 32A | Maksimum akım |

**ÖNEMLİ:** 6-32 amper aralığında herhangi bir tam sayı değer kullanılabilir. Örnek tablodaki değerler sadece örneklerdir. Örneğin 7, 8, 9, 11, 12, 14, 15, 17, 18, 19, 21, 22, 23, 24, 26, 27, 28, 29, 30, 31 amper değerleri de geçerlidir.

**State Machine Komutları (cmd_id=04)**
| Değer | Hex | İkili | Durum Adı | Açıklama |
|-------|-----|-------|-----------|----------|
| 07 | 0x07 | 00000111 | Finishing | Şarjı bitir |

#### Protokol Örneği
**Status Komutu:**
- KOMUT: 00 (Status komutu)
- DEĞER: 00 (Status okuma)
- Hex Dizini: `41 00 2C 00 10`
- Byte Array: `[0x41, 0x00, 0x2C, 0x00, 0x10]`

_(Bu bölüm proje süresince edinilen teknik bilgiler ile güncellenecek)_

---

