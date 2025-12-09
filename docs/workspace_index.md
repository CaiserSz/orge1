# Workspace Index - Proje Yapısı ve Dosya Açıklamaları

**Oluşturulma Tarihi:** 2025-12-09 02:45:00
**Son Güncelleme:** 2025-12-10 01:55:00
**Version:** 2.0.0
**Amaç:** Workspace'teki tüm dosya ve klasörlerin hızlı referansı ve açıklamaları

---

## 📁 Klasör Yapısı

```
/home/basar/charger/
├── api/                    # REST API modülleri
├── data/                   # Veri dosyaları (JSON, DB, vb.)
├── esp32/                  # ESP32 iletişim ve protokol modülleri
├── logs/                   # Log dosyaları
├── meter/                  # Enerji ölçüm modülü
├── ocpp/                   # OCPP protokol implementasyonu
├── scripts/                # Sistem script'leri ve servis dosyaları
├── tests/                  # Test dosyaları ve test sonuçları
├── todo/                   # Proje yönetimi ve görev takibi
├── docs/                   # Dokümantasyon (API, mimari, standartlar)
├── reports/                # Analiz ve audit raporları
└── env/                    # Python virtual environment (gitignore)
```

---

## 📄 Kök Dizin Dosyaları

### Dokümantasyon Dosyaları

#### `project_info_20251208_145614.md`
- **Ne:** Ana proje bilgileri ve teknik dokümantasyon
- **Amaç:** Tüm proje bilgileri, analizler, değerlendirmeler ve teknik detayların tek kaynağı
- **İçerik:**
  - Proje genel bilgileri
  - Sistem mimarisi
  - ESP32-RPi protokol detayları
  - API endpoint'leri
  - Analizler ve değerlendirmeler (Deep Dive, State Logic, Session Management)
  - WiFi Failover sistemi
  - Versiyon geçmişi
- **Ne Zaman:** 2025-12-08'de oluşturuldu, sürekli güncelleniyor
- **Versiyon:** 1.5.0
- **İlgili Dosyalar:** `.cursorrules`, `todo/master.md`

#### `README.md`
- **Ne:** Proje genel tanıtımı ve hızlı başlangıç kılavuzu
- **Amaç:** Projeye yeni başlayanlar için genel bakış ve kurulum talimatları
- **İçerik:** Proje açıklaması, kurulum, kullanım, dokümantasyon linkleri
- **Ne Zaman:** 2025-12-08'de oluşturuldu, güncellenmeli

---

## 📁 Klasörler ve Dosyalar

### 📊 `reports/` Klasörü - Analiz ve Audit Raporları

Tüm analiz, audit ve değerlendirme raporları bu klasörde toplanmıştır.

#### Audit Raporları
- **`AUDIT_REPORT_20251209.md`** - Security audit raporu
- **`LOGGING_AUDIT.md`** - Logging sistemi audit raporu
- **`PRE_LOGGING_AUDIT.md`** - Logging öncesi çalışmalar audit raporu
- **`DOCUMENTATION_AUDIT.md`** - Dokümantasyon audit raporu
- **`DOCUMENTATION_UPDATE_AUDIT_20251209.md`** - Dokümantasyon güncelleme audit raporu

#### Analiz Raporları
- **`MULTI_EXPERT_ANALYSIS.md`** - Multi-expert analiz raporu
- **`DEEP_DIVE_ANALYSIS_20251210.md`** - Deep dive analiz raporu
- **`DEEPDIVE_ANALYSIS_REPORT.md`** - Deep dive analiz raporu (alternatif)
- **`ANALYSIS_SUMMARY.md`** - Analiz özeti
- **`RPI_STRATEGIC_ANALYSIS.md`** - RPi stratejik analiz raporu
- **`RPI_ACTION_PLAN.md`** - RPi aksiyon planı
- **`PYTHON_SIDE_REVIEW.md`** - Python tarafı inceleme raporu

#### ESP32 Raporları
- **`ESP32_FIRMWARE_ADVISORY_REPORT.md`** - ESP32 firmware tavsiye raporu
- **`HARDFAULT_END_VERIFICATION.md`** - HARDFAULT_END doğrulama raporu

#### Authorization Raporları
- **`AUTHORIZATION_LOGIC_REVISED.md`** - Authorization mantık revizyonu
- **`AUTHORIZATION_WORKAROUND_EXPLAINED.md`** - Authorization workaround açıklaması

#### Durum Raporları
- **`PROJECT_STATUS_SUMMARY.md`** - Proje durum özeti
- **`NEXT_STEPS_SUMMARY.md`** - Sıradaki adımlar özeti

### 📚 `docs/` Klasörü - Dokümantasyon

#### Ana Dokümantasyon
- **`api_reference.md`** - API referans dokümantasyonu
- **`architecture.md`** - Sistem mimarisi dokümantasyonu
- **`deployment.md`** - Deployment kılavuzu
- **`troubleshooting.md`** - Sorun giderme kılavuzu

#### Ek Dokümantasyon
- **`api_examples.md`** - API kullanım örnekleri
- **`meter_setup.md`** - Meter kurulum dokümantasyonu
- **`wifi_troubleshooting.md`** - WiFi sorun giderme kılavuzu
- **`git_github_improvement_plan.md`** - Git/GitHub iyileştirme planı
- **`workspace_index.md`** - Workspace indeksi (bu dosya)
- **`workspace_reorganization_plan.md`** - Workspace reorganizasyon planı

#### Standartlar (`docs/standards/`)
- **`CODE_DOCUMENTATION_STANDARDS.md`** - Kod ve dokümantasyon standartları
- **`BACKUP_ROLLBACK_STANDARDS.md`** - Yedekleme ve geri dönüş standartları
- **`WORKSPACE_MANAGEMENT_STANDARDS.md`** - Workspace yönetimi standartları

---

## 📄 Kök Dizin Dosyaları (Güncellenmiş)

### Ana Dokümantasyon
- **`README.md`** - Proje genel tanıtımı ve hızlı başlangıç kılavuzu
- **`CHANGELOG.md`** - Değişiklik geçmişi
- **`CONTRIBUTING.md`** - Katkı rehberi
- **`project_info_20251208_145614.md`** - Ana proje bilgileri ve teknik dokümantasyon
- **İçerik:**
  - Donanım bağlantıları (GPIO12/13, MAX13487, ABB Meter)
  - Raspberry Pi UART5 yapılandırması
  - Modbus RTU protokol bilgileri
  - Test ve doğrulama adımları
  - Sorun giderme rehberi
  - Araştırma bulguları
- **Ne Zaman:** 2025-12-09'da oluşturuldu ve güncellendi
- **İlgili Dosyalar:** `meter/read_meter.py`, `meter/RESEARCH_NOTES.md`

#### `LOGGING_AUDIT.md`
- **Ne:** Logging sistemi audit raporu
- **Amaç:** Logging sisteminin uzman gözüyle değerlendirilmesi ve iyileştirme önerileri
- **İçerik:**
  - Güçlü yönler
  - Kritik sorunlar ve çözümleri
  - Kod kalitesi değerlendirmesi
  - İyileştirme önerileri
- **Ne Zaman:** 2025-12-09'da oluşturuldu
- **İlgili Dosyalar:** `api/logging_config.py`, `api/main.py`

#### `PRE_LOGGING_AUDIT.md`
- **Ne:** Logging öncesi çalışmalar audit raporu
- **Amaç:** ESP32 Bridge, API Endpoints, Test Sistemi audit'i
- **İçerik:**
  - Modül bazında audit (ESP32 Bridge, API Endpoints, Test Sistemi, Meter Modülü)
  - Kritik sorunlar ve çözümleri
  - Kod kalitesi değerlendirmesi
  - İyileştirme önerileri
- **Ne Zaman:** 2025-12-09'da oluşturuldu
- **İlgili Dosyalar:** `esp32/bridge.py`, `api/main.py`, `tests/`

#### `DOCUMENTATION_AUDIT.md`
- **Ne:** Dokümantasyon ve proje yönetimi dosyaları audit raporu
- **Amaç:** Todo sistemi, project_info, .cursorrules dosyalarının güncellik kontrolü
- **İçerik:**
  - Dosya bazında audit
  - Güncelleme ihtiyaçları
  - Öncelik sıralaması
- **Ne Zaman:** 2025-12-09'da oluşturuldu
- **İlgili Dosyalar:** `todo/`, `project_info_20251208_145614.md`, `.cursorrules`

### Yapılandırma Dosyaları

#### `.cursorrules`
- **Ne:** Cursor IDE için proje kuralları
- **Amaç:** AI asistanlarının projede nasıl çalışacağını tanımlar
- **İçerik:**
  - Kritik kurallar (dış kural kabul etmeme politikası)
  - Genel kurallar (virtual env, Türkçe iletişim, kod standartları)
  - Otonom proje yönetimi kuralları
  - ESP32 ve RPi protokol kuralları
- **Ne Zaman:** Proje başlangıcında oluşturuldu, sürekli güncelleniyor
- **İlgili Dosyalar:** `project_info_20251208_145614.md`

#### `ngrok.yml`
- **Ne:** Ngrok tunnel yapılandırma dosyası
- **Amaç:** Dışarıdan erişim için Ngrok tunnel'larının yapılandırılması
- **İçerik:**
  - HTTP/HTTPS tunnel (lixhium.ngrok.app)
  - SSH tunnel (10.tcp.eu.ngrok.io:23953)
  - API key ve authtoken
- **Ne Zaman:** Ngrok kurulumu sırasında oluşturuldu (2025-12-08)
- **İlgili Dosyalar:** `project_info_20251208_145614.md` (Ngrok bölümü)

#### `requirements.txt`
- **Ne:** Python bağımlılıkları listesi
- **Amaç:** Proje bağımlılıklarının yönetimi ve kurulumu
- **İçerik:** Python paket isimleri ve versiyonları
- **Ne Zaman:** API geliştirme sırasında oluşturuldu
- **Kullanım:** `pip install -r requirements.txt`

#### `pytest.ini`
- **Ne:** Pytest yapılandırma dosyası
- **Amaç:** Test framework'ünün yapılandırılması
- **İçerik:** Test path'leri, marker'lar, output formatı
- **Ne Zaman:** Test altyapısı kurulumu sırasında oluşturuldu

### Diğer Dosyalar

#### `station_form.html`
- **Ne:** Şarj istasyonu bilgileri için statik HTML formu
- **Amaç:** İstasyon bilgilerini girmek ve görüntülemek için web formu
- **İçerik:** Form alanları, JavaScript API entegrasyonu
- **Ne Zaman:** API geliştirme sırasında oluşturuldu
- **İlgili Dosyalar:** `api/main.py` (`/form` endpoint), `api/station_info.py`

#### `api_test.html`
- **Ne:** API test web sayfası
- **Amaç:** Dışarıdan API'leri test etmek için modern, responsive web arayüzü
- **İçerik:**
  - Modern responsive UI (gradient arka plan, modern butonlar)
  - Tüm endpoint'ler için test butonları (System, Charge Control, Current Control)
  - Request/response body görüntüleme (JSON format)
  - Edit edilebilir cURL komut önizleme
  - Auto API key loading (backend'den)
  - Debounce optimizasyonu (300ms)
  - Input validation (amperage 6-32A)
  - Shell command injection koruması (escapeShellString)
- **Ne Zaman:** 2025-12-09'da oluşturuldu
- **Versiyon:** 1.0.0
- **İlgili Dosyalar:** `api/main.py` (`/test` endpoint), `api/auth.py`
- **Endpoint:** `GET /test` (https://lixhium.ngrok.app/test)

---

## 📂 Klasör Detayları

### `api/` - REST API Modülleri

**Amaç:** FastAPI tabanlı REST API endpoint'leri ve modülleri

#### `api/main.py`
- **Ne:** Ana FastAPI uygulaması
- **Amaç:** REST API endpoint'lerinin tanımlanması ve yönetimi
- **İçerik:**
  - API endpoint'leri (`/api/status`, `/api/charge/start`, `/api/charge/stop`, `/api/maxcurrent`, vb.)
  - ESP32 bridge entegrasyonu (dependency injection pattern)
  - Request/Response modelleri
  - Error handling (production-safe exception handler)
  - API logging middleware
- **Ne Zaman:** 2025-12-08'de oluşturuldu, 2025-12-09'da güncellendi
- **Versiyon:** 1.1.0
- **İlgili Dosyalar:** `esp32/bridge.py`, `api/station_info.py`, `api/logging_config.py`

#### `api/logging_config.py`
- **Ne:** Structured logging konfigürasyonu ve helper fonksiyonlar
- **Amaç:** JSON formatında structured logging, log rotation, thread-safe logging
- **İçerik:**
  - JSONFormatter (JSON formatında loglama)
  - Log rotation (10MB, 5 yedek dosya)
  - Thread-safe logging mekanizması
  - Helper fonksiyonlar (log_api_request, log_esp32_message, log_event)
  - Ayrı logger'lar (api, esp32, system)
- **Ne Zaman:** 2025-12-09'da oluşturuldu
- **Versiyon:** 1.0.0
- **İlgili Dosyalar:** `api/main.py`, `esp32/bridge.py`
- **Log Dosyaları:** `logs/api.log`, `logs/esp32.log`, `logs/system.log`

#### `api/station_info.py`
- **Ne:** İstasyon bilgileri yönetim modülü
- **Amaç:** Statik istasyon bilgilerinin yüklenmesi ve kaydedilmesi
- **İçerik:**
  - `load_station_info()` - JSON'dan istasyon bilgilerini yükle
  - `save_station_info()` - İstasyon bilgilerini JSON'a kaydet
  - `get_station_info()` - İstasyon bilgilerini döndür
- **Ne Zaman:** 2025-12-08'de oluşturuldu
- **İlgili Dosyalar:** `data/station_info.json`, `api/main.py` (`/api/station/info` endpoint)

---

### `esp32/` - ESP32 İletişim ve Protokol

**Amaç:** ESP32 ile USB seri port üzerinden iletişim modülleri

#### `esp32/bridge.py`
- **Ne:** ESP32-RPi bridge modülü
- **Amaç:** ESP32 ile USB seri port üzerinden iletişim köprüsü
- **İçerik:**
  - `ESP32Bridge` sınıfı
  - Serial port bağlantı yönetimi
  - Komut gönderme fonksiyonları (authorization, current set, charge stop, status)
  - Status mesajı parsing
  - Thread-based monitoring
- **Ne Zaman:** 2025-12-08'de oluşturuldu
- **Versiyon:** 1.0.0
- **İlgili Dosyalar:** `esp32/protocol.json`, `api/main.py`

#### `esp32/protocol.json`
- **Ne:** ESP32 protokol tanımları (JSON formatında)
- **Amaç:** Komut tanımları, byte array formatları, protokol detayları
- **İçerik:**
  - Protokol formatı ve sabitler
  - Komut tanımları (status, authorization, current_set_range, charge_stop)
  - Status mesajı formatı
- **Ne Zaman:** 2025-12-08'de oluşturuldu
- **İlgili Dosyalar:** `esp32/bridge.py`, `esp32/Commercial_08122025.ino`

#### `esp32/Commercial_08122025.ino`
- **Ne:** ESP32 firmware kodu (Arduino)
- **Amaç:** ESP32 şarj istasyonu kontrol ünitesi firmware'i
- **İçerik:**
  - State machine implementasyonu
  - Control Pilot ve Proximity Pilot kontrolü
  - RFID kart okuma
  - Relay ve lock kontrolü
  - USB seri port iletişim protokolü
- **Ne Zaman:** 2025-12-08'de (firmware versiyonu)
- **Satır Sayısı:** ~1438 satır
- **İlgili Dosyalar:** `esp32/protocol.json`, `esp32/bridge.py`

---

### `data/` - Veri Dosyaları

**Amaç:** Uygulama verilerinin saklandığı klasör

#### `data/station_info.json`
- **Ne:** İstasyon bilgileri JSON dosyası
- **Amaç:** Statik istasyon bilgilerinin saklanması
- **İçerik:** İstasyon ID, adres, koordinatlar, vb.
- **Ne Zaman:** API geliştirme sırasında oluşturuldu
- **İlgili Dosyalar:** `api/station_info.py`, `api/main.py`

---

### `logs/` - Log Dosyaları

**Amaç:** Sistem log dosyalarının saklandığı klasör

#### `logs/system.log`
- **Ne:** Sistem log dosyası
- **Amaç:** Sistem olaylarının loglanması
- **İçerik:** Sistem mesajları, hatalar, uyarılar
- **Format:** JSON (structured logging)
- **Rotation:** 10MB maksimum, 5 yedek dosya

#### `logs/api.log`
- **Ne:** API istekleri ve yanıtları log dosyası
- **Amaç:** API endpoint'lerinin istek ve yanıtlarının loglanması
- **İçerik:** HTTP metodları, path'ler, status kodları, response time'lar
- **Format:** JSON (structured logging)
- **Rotation:** 10MB maksimum, 5 yedek dosya
- **Not:** Şarj başlatma/bitirme istekleri güvenlik nedeniyle loglanmaz

#### `logs/esp32.log`
- **Ne:** ESP32 mesajları log dosyası
- **Amaç:** ESP32 ile iletişim mesajlarının loglanması
- **İçerik:** Komut gönderme (tx), status mesajları (rx), bağlantı/bağlantı kesme olayları
- **Format:** JSON (structured logging)
- **Rotation:** 10MB maksimum, 5 yedek dosya

#### `logs/meter.log`
- **Ne:** Enerji ölçüm log dosyası
- **Amaç:** Meter okuma verilerinin loglanması
- **İçerik:** Enerji ölçüm verileri
- **Durum:** Henüz aktif değil (meter entegrasyonu devam ediyor)

---

### `meter/` - Enerji Ölçüm Modülü

**Amaç:** ABB Meter RS485 entegrasyonu ve Modbus RTU protokolü ile veri okuma

#### `meter/read_meter.py`
- **Ne:** ABB Meter RS485 okuma modülü
- **Amaç:** ABB B23 112-100 meter'dan RS485 üzerinden Modbus RTU protokolü ile veri okuma
- **Durum:** ✅ Implement edildi (2025-12-09)
- **İçerik:**
  - ABBMeterReader sınıfı
  - Modbus RTU protokol implementasyonu
  - RS485 RTS kontrolü (MAX13487 için)
  - CRC16 hesaplama
  - Register okuma fonksiyonları
- **Ne Zaman:** 2025-12-09'da oluşturuldu ve geliştirildi
- **İlgili Dosyalar:** `METER_SETUP.md`, `meter/RESEARCH_NOTES.md`

#### `meter/RESEARCH_NOTES.md`
- **Ne:** Meter araştırma notları ve bulgular
- **Amaç:** Web araştırması bulguları, sorun giderme notları ve çözüm önerileri
- **İçerik:**
  - GPIO pin fonksiyonu sorunları
  - RS485 sonlandırma dirençleri
  - MAX13487 DE/RE kontrol pinleri
  - RTS sinyal senkronizasyonu
  - Topraklama ve parazit kontrolü
- **Ne Zaman:** 2025-12-09'da oluşturuldu
- **İlgili Dosyalar:** `METER_SETUP.md`, `meter/read_meter.py`

#### `meter/test_meter_scan.py`
- **Ne:** Meter tarama ve test scripti
- **Amaç:** Farklı baudrate ve slave ID kombinasyonlarını test etme
- **İçerik:** Otomatik tarama scripti (9600, 19200, 4800 baudrate, slave ID 1-247)
- **Ne Zaman:** 2025-12-09'da oluşturuldu
- **Kullanım:** `python3 meter/test_meter_scan.py`

#### `meter/test_parity.py`
- **Ne:** Parity ayarları test scripti
- **Amaç:** Farklı parity ayarlarını (EVEN, ODD, NONE) test etme
- **İçerik:** Parity kombinasyonları test scripti
- **Ne Zaman:** 2025-12-09'da oluşturuldu
- **Kullanım:** `python3 meter/test_parity.py`

---

### `ocpp/` - OCPP Protokol Implementasyonu

**Amaç:** OCPP 1.6J ve 2.0.1 protokol desteği

#### `ocpp/main.py`
- **Ne:** OCPP ana modülü
- **Amaç:** OCPP WebSocket bağlantı yönetimi ve mesaj işleme
- **Durum:** Temel yapı oluşturuldu, geliştirme devam ediyor
- **Planlanan:** Faz 3'te tam implementasyon

#### `ocpp/handlers.py`
- **Ne:** OCPP mesaj handler'ları
- **Amaç:** OCPP mesajlarının işlenmesi
- **Durum:** Henüz implement edilmedi
- **Planlanan:** Faz 3'te geliştirilecek

#### `ocpp/states.py`
- **Ne:** OCPP state yönetimi
- **Amaç:** OCPP state machine yönetimi
- **Durum:** Henüz implement edilmedi
- **Planlanan:** Faz 3'te geliştirilecek

---

### `scripts/` - Sistem Script'leri

**Amaç:** Sistem script'leri ve systemd servis dosyaları

#### `scripts/wifi_failover_monitor.py`
- **Ne:** WiFi failover monitoring script'i
- **Amaç:** WiFi bağlantısını izleme ve otomatik failover
- **İçerik:**
  - Aktif WiFi bağlantısını izleme
  - Internet erişimi kontrolü (5 saniyede bir)
  - 20 saniye internet erişimi yoksa failover
  - Otomatik WiFi ağı değiştirme
- **Ne Zaman:** 2025-12-08'de oluşturuldu
- **İlgili Dosyalar:** `scripts/wifi-failover-monitor.service`

#### `scripts/wifi-failover-monitor.service`
- **Ne:** WiFi failover monitor systemd servis dosyası
- **Amaç:** WiFi failover script'inin sistem servisi olarak çalışması
- **İçerik:** Systemd servis tanımı (unit file)
- **Ne Zaman:** 2025-12-08'de oluşturuldu
- **Kullanım:** `systemctl enable/start wifi-failover-monitor.service`
- **İlgili Dosyalar:** `scripts/wifi_failover_monitor.py`

---

### `tests/` - Test Dosyaları

**Amaç:** Unit testler, integration testler ve test sonuçları

#### `tests/__init__.py`
- **Ne:** Test paketi başlatıcı
- **Amaç:** `tests` klasörünü Python paketi yapmak

#### `tests/test_esp32_bridge.py`
- **Ne:** ESP32 bridge unit testleri
- **Amaç:** ESP32 bridge modülünün test edilmesi
- **İçerik:** Hex kod doğrulama, komut gönderme testleri
- **Ne Zaman:** Deep dive kontrolleri sırasında oluşturuldu (2025-12-09)

#### `tests/test_api_endpoints.py`
- **Ne:** API endpoint integration testleri
- **Amaç:** API endpoint'lerinin test edilmesi
- **İçerik:** Mock ESP32 bridge ile API testleri
- **Ne Zaman:** Deep dive kontrolleri sırasında oluşturuldu (2025-12-09)

#### `tests/test_state_logic.py`
- **Ne:** State logic testleri
- **Amaç:** State-dependent logic'in doğru çalıştığını doğrulama
- **İçerik:** Farklı STATE değerleri için API davranış testleri
- **Ne Zaman:** State logic analizi sırasında oluşturuldu (2025-12-09)

#### `tests/test_error_handling.py`
- **Ne:** Error handling testleri
- **Amaç:** Hata durumlarının doğru yönetildiğini doğrulama
- **İçerik:** ESP32 bağlantı hataları, serial communication hataları, timeout testleri
- **Ne Zaman:** Deep dive kontrolleri sırasında oluşturuldu (2025-12-09)

#### `tests/test_thread_safety.py`
- **Ne:** Thread safety testleri
- **Amaç:** Concurrent access'in güvenli olduğunu doğrulama
- **İçerik:** Status access, lock mechanism testleri
- **Ne Zaman:** Deep dive kontrolleri sırasında oluşturuldu (2025-12-09)

#### `tests/test_status_parsing.py`
- **Ne:** Status parsing testleri
- **Amaç:** ESP32 status mesajlarının doğru parse edildiğini doğrulama
- **İçerik:** Edge case'ler, hatalı formatlı mesajlar, Unicode testleri
- **Ne Zaman:** Deep dive kontrolleri sırasında oluşturuldu (2025-12-09)

#### `tests/test_integration.py`
- **Ne:** Integration testleri
- **Amaç:** Tam şarj akışı senaryolarının test edilmesi
- **İçerik:** End-to-end testler, hata kurtarma akışları
- **Ne Zaman:** Deep dive kontrolleri sırasında oluşturuldu (2025-12-09)

---

### `todo/` - Proje Yönetimi

**Amaç:** Proje yönetimi, görev takibi ve otonom çalışma sistemi

#### `todo/START_HERE.md`
- **Ne:** Projeye devam etmek için başlangıç noktası
- **Amaç:** AI asistanlarının projeye devam ederken ilk okuması gereken dosya
- **İçerik:** Proje durumu, nerede kaldık, sonraki adımlar
- **Öncelik:** ⚡ EN ÖNEMLİ DOSYA - ÖNCE BUNU OKU!

#### `todo/master.md`
- **Ne:** Todo sistemi genel bilgileri
- **Amaç:** Todo sisteminin açıklaması ve kullanım kuralları
- **İçerik:** Dosya yapısı, görev formatı, durumlar, kurallar

#### `todo/master_next.md`
- **Ne:** Sonraki yapılacaklar listesi
- **Amaç:** Öncelik sırasına göre sıralanmış görevler
- **İçerik:** Fazlara ayrılmış görevler (Faz 1-6)
- **Güncelleme:** Görevler tamamlandıkça `master_done.md`'ye taşınır

#### `todo/master_live.md`
- **Ne:** Şu anda aktif olarak yapılan işler
- **Amaç:** Aktif görevlerin takibi (maksimum 2-3 görev)
- **İçerik:** Şu anda çalışılan görevler
- **Güncelleme:** Görev başladığında buraya taşınır, tamamlandığında `master_done.md`'ye taşınır

#### `todo/master_done.md`
- **Ne:** Tamamlanan işler listesi
- **Amaç:** Tamamlanan görevlerin kaydı (tarih ve detaylarla)
- **İçerik:** Tamamlanan görevler, tarihler, detaylar
- **Güncelleme:** Görev tamamlandığında buraya taşınır

#### `todo/checkpoint.md`
- **Ne:** Nerede kaldık? Hızlı durum kontrolü
- **Amaç:** Projenin hızlı durum kontrolü
- **İçerik:** Son yapılan işler, aktif görevler, sonraki adımlar

#### `todo/project_state.md`
- **Ne:** Detaylı proje durumu ve ilerleme takibi
- **Amaç:** Projenin detaylı durum analizi
- **İçerik:** Fazlar, tamamlanma yüzdeleri, blokajlar, riskler

#### `todo/ai_workflow.md`
- **Ne:** AI asistanları için çalışma akışı ve kurallar
- **Amaç:** AI asistanlarının nasıl çalışacağını tanımlar
- **İçerik:** Otonom çalışma kuralları, görev seçimi, tamamlama adımları

#### `todo/expert_recommendations.md`
- **Ne:** Kıdemli uzman önerileri ve best practices
- **Amaç:** Proje geliştirme için öneriler ve best practices
- **İçerik:** Mimari öneriler, kod kalitesi, güvenlik, performans

---

## 🔗 Dosya İlişkileri

### API Akışı
```
api/main.py → esp32/bridge.py → esp32/protocol.json
           → api/station_info.py → data/station_info.json
           → station_form.html
```

### ESP32 İletişim Akışı
```
esp32/bridge.py → esp32/protocol.json
                → /dev/ttyUSB0 (ESP32)
                → esp32/Commercial_08122025.ino
```

### Test Akışı
```
tests/test_*.py → api/main.py (mock)
                → esp32/bridge.py (mock)
                → pytest.ini
```

### Proje Yönetimi Akışı
```
todo/START_HERE.md → todo/checkpoint.md
                  → todo/project_state.md
                  → todo/master_live.md
                  → todo/master_next.md
                  → todo/master_done.md
```

---

## 📊 Dosya İstatistikleri

### Toplam Dosya Sayıları (yaklaşık)
- **Python Dosyaları:** ~15
- **Markdown Dosyaları:** ~20
- **JSON Dosyaları:** ~3
- **Test Dosyaları:** ~10
- **Konfigürasyon Dosyaları:** ~5

### Klasör Yapısı
- **Toplam Klasör:** 10
- **Derinlik:** 2-3 seviye

---

## 🔄 Güncelleme Kuralları

### Ne Zaman Güncellenmeli?
1. **Yeni dosya/klasör eklendiğinde**
2. **Dosya amacı değiştiğinde**
3. **Dosya silindiğinde**
4. **Önemli değişiklikler olduğunda**

### Nasıl Güncellenmeli?
1. İlgili bölümü bul
2. Dosya/klasör bilgilerini güncelle
3. İlişkileri kontrol et
4. Versiyon numarasını artır
5. Git commit yap

---

## 💡 Kullanım Önerileri

### Yeni Bir AI Asistanı İçin
1. `todo/START_HERE.md` dosyasını oku
2. `project_info_20251208_145614.md` dosyasını oku
3. Bu dosyayı (`WORKSPACE_INDEX.md`) referans olarak kullan
4. İlgili klasör/dosyayı bul ve çalışmaya başla

### Dosya Bulma
- **API ile ilgili:** `api/` klasörü
- **ESP32 ile ilgili:** `esp32/` klasörü
- **Test ile ilgili:** `tests/` klasörü
- **Proje yönetimi:** `todo/` klasörü
- **Dokümantasyon:** Kök dizindeki `.md` dosyaları

### Hızlı Referans
- **Ne olduğunu öğrenmek için:** Bu dosyayı oku
- **Nasıl kullanılacağını öğrenmek için:** İlgili dosyayı oku
- **Ne zaman oluşturulduğunu öğrenmek için:** Bu dosyada tarih bilgisi var
- **İlgili dosyaları bulmak için:** "İlgili Dosyalar" bölümüne bak

---

**Son Güncelleme:** 2025-12-09 02:45:00
**Versiyon:** 1.0.0
**Sonraki Güncelleme:** Yeni dosya/klasör eklendiğinde

