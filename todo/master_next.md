# Sonraki Yapılacaklar

**Son Güncelleme:** 2025-12-25 06:23:00

**Not:** Detaylı kıdemli uzman önerileri için `expert_recommendations.md` dosyasına bakınız.

---

## Öncelikli Görevler

### Öncelik 1: ESP32 İletişim Dayanıklılığı — USB + GPIO UART Failover (2025-12-24)

- [ ] **Görev:** ESP32 GPIO UART (RPi GPIO14/15 ↔ ESP32 GPIO34/21) linkini aktif et (firmware + RPi bridge)
  - Açıklama: USB (`/dev/ttyUSB0`) yanında UART0 (`/dev/serial0` → şu sistemde `/dev/ttyS0`) fiziksel hat var; USB koparsa GPIO UART üzerinden devam etmek isteniyor.
  - Öncelik: 1 (Yüksek)
  - Tahmini Süre: 2-4 saat
  - Durum: ⏸️ Ertelendi (kullanıcı tetiklediğinde devam)
  - Bulgular:
    - RPi tarafında `/dev/serial0 -> /dev/ttyS0` mevcut ve dialout erişimi var (boş görünüyor).
    - Mevcut sahada `/dev/serial0` üzerinden 115200 ile okuma + `41 00 2C 00 10` status komutu denemesinde yanıt alınamadı (0 byte).
    - **Aktif firmware (saha):** `esp32/Commercial_V3.ino` (ESP32 üzerinde yüklü). `Commercial_V4.ino` geldiğinde SSOT güncellenecek.
    - Legacy not: `esp32/Commercial_08122025.ino` içinde `USE_DUAL_UART` açık olsa da GPIO UART command handler blokları yorum satırında; `sendStat()` sadece `SerialUSB`’a yazıyor. Bu nedenle o sürümde GPIO UART’ın pratikte “aktif” olmaması beklenir.
  - Aksiyon Planı:
    - ESP32 firmware: SerialGPIO üzerinden komut okuma + ACK/STAT yanıtı gönderme (gerekirse status broadcast’ını iki arayüze de verme).
    - RPi bridge: USB primary + `/dev/serial0` fallback port seçimi ve reconnect failover.

### Öncelik 1: Arduino CLI / ESP32 Core için Disk Kapasitesi (2025-12-24)

- [ ] **Görev:** RPi depolama kapasitesini artır (SSD/root partition) veya Arduino toolchain dizinini daha büyük diske taşı
  - Açıklama: `arduino-cli core install esp32:esp32` toolchain çok büyük (tek başına `~/.arduino15` ~5-6GB). Kurulum sırasında “no space left on device” yaşandı ve root partition hızla doluyor.
  - Öncelik: 1 (Yüksek)
  - Tahmini Süre: 30-90 dk (disk büyütme/mount/taşıma yaklaşımına göre)
  - Durum: ⏸️ Ertelendi (kullanıcı tetiklediğinde devam)
  - Öneri:
    - SSD/root partition büyüt (en az birkaç GB boş pay hedefle) **veya**
    - `~/.arduino15` dizinini harici diske taşı + symlink/mount ile aynı path’i koru (başka AI’lar “yok” sanıp tekrar kurmaya kalkmasın diye).

### Öncelik 3: Firmware SSOT / Workspace Hijyeni (2025-12-24)

- [x] **Görev:** ESP32 firmware için tek SSOT belirle ve kopya `.ino` dosyalarını temizle/isim standardına uydur
  - Açıklama: Workspace’te birden fazla “Commercial” `.ino` kopyası var. SSOT netleştirildi ve `.ino` dosyalarının git’te track edilmemesi için hijyen uygulandı.
  - Öncelik: 3 (Orta/Düşük)
  - Tahmini Süre: 30-60 dk
  - Durum: ✅ Tamamlandı (2025-12-25)
  - SSOT (şu an): `esp32/Commercial_V3.ino` (ESP32 üzerinde yüklü)
  - Not: `Commercial_V4.ino` geldiğinde SSOT güncellenecek.
  - Git hijyeni:
    - `esp32/*.ino` `.gitignore` içine eklendi (firmware dosyaları cihazda “doküman” olarak kalsın ama repo’da track edilmesin).
    - Daha önce track edilen `esp32/Commercial_08122025.ino` git index’ten çıkarıldı (dosya cihazda kalır, repo’da görünmez).

### Öncelik 2: Test Coverage Boşlukları (2025-12-16) - Meter/OCPP/DB

### Öncelik 2: Standart Uyarı Eşiği Yakın Dosyalar (2025-12-22) - Yeni Uyarılar

- [x] **Görev:** `api/database/maintenance_queries.py` satır limiti payı açma (standards uyarısını kapat)
  - Açıklama: Dosya satır sayısı 499→399 (SQL string’leri kompaktlaştırıldı + tekrarlar azaltıldı). Ek olarak OCPP profile insert path’i için placeholder sayısı düzeltildi ve test eklendi.
  - Öncelik: 2 (Yüksek)
  - Tahmini Süre: 1-2 saat
  - Durum: ✅ Tamamlandı (2025-12-25)
  - Not: Yeni dosya açmadan çözüldü (repo kuralı). İleride gerekirse modüler refactor yapılabilir.

- [ ] **Görev:** `tests/test_integration.py` dosyasını test suite’e böl
  - Açıklama: `standards_auto_check` uyarısı: 416 satır (limit 500). Entegrasyon testleri büyüyor; parçalanmalı.
  - Öncelik: 2 (Orta)
  - Tahmini Süre: 1-2 saat
  - Durum: 🟡 Uyarı eşiği yakın

- [ ] **Görev:** `api/routers/test.py` (Admin UI) dosyasını sadeleştir / böl
  - Açıklama: `standards_auto_check` uyarısı kapatıldı: 464 → 399 satır. Tek dosya kuralına uyarak (yeni dosya oluşturmadan) kod sıkılaştırıldı.
  - Öncelik: 2 (Orta)
  - Tahmini Süre: 1-2 saat
  - Durum: ✅ Tamamlandı (2025-12-25)
  - Not: İleride gerekirse router/HTML ayrıştırma (kural/istisna açılırsa) değerlendirilebilir.

- [ ] **Görev:** `tests/test_api_endpoints.py` dosyasını test suite’e böl (uyarı eşiği yeniden yakın)
  - Açıklama: `standards_auto_check` uyarısı: 467 satır (limit 500). Yeni API testleri eklendikçe büyüyor; bakım riski artıyor.
  - Öncelik: 2 (Orta)
  - Tahmini Süre: 1-2 saat
  - Durum: 🟡 Uyarı eşiği yakın
  - Not: Yeni dosya oluşturma kuralı/istisnası netleşince testleri modüler dosyalara bölmek (örn. meter/api/status).

- [ ] **Görev:** `tests/test_api_main_endpoints.py` dosyasını test suite’e böl
  - Açıklama: `standards_auto_check` uyarısı: 410 satır (limit 500). Endpoint testleri büyüyor; parçalanmalı.
  - Öncelik: 2 (Orta)
  - Tahmini Süre: 1-2 saat
  - Durum: 🟡 Uyarı eşiği yakın

### Öncelik 0: Secret/Config Hijyeni (2025-12-19) - `.env` repo içinde track ediliyor

- [ ] **Görev:** `SECRET_API_KEY` rotasyonu + (gerekirse) git history/incident değerlendirmesi
  - Açıklama: `.env` tracked olduğu için mevcut `SECRET_API_KEY` değeri “kompromize” kabul edilmeli. Yeni anahtar üret, eskiyi geçersiz kıl. History rewrite gerekip gerekmediğini değerlendir (repo policy’ye göre).
  - Öncelik: 0 (Acil)
  - Tahmini Süre: 30-60 dk
  - Durum: ⏸️ Ertelendi (test aşaması; risk kabul edildi)

- [x] **Görev:** Admin UI (HTTP Basic) parolasını güçlü bir parolayla değiştir
  - Açıklama: Erişim/test amacıyla station-side Admin UI için prod DB’de admin parolası geçici olarak default’a çekildi. Güvenlik için güçlü, benzersiz bir parola ile `/admin` üzerinden değiştirilmelidir.
  - Öncelik: 0 (Acil)
  - Tahmini Süre: 5-10 dk
  - Durum: ✅ Tamamlandı (2025-12-25)

### Öncelik 0: Sistem Sağlık Tespitleri (2025-12-15) - Güç Beslemesi ve Servis Tutarlılığı

- [ ] **Görev:** RPi undervoltage kalıcı çözüm (hardware) — PSU/kablo/USB yükü doğrula + reboot + teyit
  - Açıklama: Bu kısım fiziksel müdahale gerektirir. Amaç: undervoltage/throttling durumunu kalıcı olarak sıfırlamak.
  - Öncelik: 0 (Acil)
  - Tahmini Süre: 30-60 dk (PSU/kablo + reboot + teyit)
  - Durum: ⏸️ Ertelendi (fiziksel erişim yok; kullanıcı uygun olduğunda bildirecek)
  - Done kriteri:
    - Reboot sonrası `vcgencmd get_throttled` → `throttled=0x0`
    - `journalctl -k --no-pager | grep -i undervoltage | tail -n 50` → yeni kayıt yok (en azından fix sonrası yeni event gözlenmiyor)
  - Notlar:
    - Öneri: resmi/kaliteli 5.1V/3A PSU + kısa/kalın USB‑C kablo; yüksek akım çeken USB cihazları için powered hub

### ✅ Kapatıldı: Standart uyarıları (2025-12-22) — satır limiti “uyarı eşiği yakın” temizlendi

### Öncelik 3: Standart Uyarıları (2025-12-16) - Uyarı Eşiği Yakın Dosyalar

- [x] **Görev:** `api/logging_config.py` satır limiti payı açma
  - Açıklama: Dosya 407 → 358 satır; `standards_auto_check` uyarısı kapatıldı.
  - Öncelik: 3 (Orta/Düşük)
  - Tahmini Süre: 1-2 saat
  - Durum: ✅ Kapatıldı (2025-12-22)

- [x] **Görev:** `api/event_detector.py` satır limiti payı açma
  - Açıklama: Dosya 477 → 390 satır; `standards_auto_check` uyarısı kapatıldı.
  - Öncelik: 3 (Orta/Düşük)
  - Tahmini Süre: 1-2 saat
  - Durum: ✅ Kapatıldı (2025-12-22)
  - Test/Doğrulama: `./env/bin/python -m py_compile api/event_detector.py` + `./env/bin/pytest -q tests/test_event_detector.py` ✅

- [x] **Görev:** `api/config.py` satır limiti payı açma
  - Açıklama: Dosya 416 → 318 satır; `standards_auto_check` uyarısı kapatıldı.
  - Öncelik: 3 (Orta/Düşük)
  - Tahmini Süre: 1-2 saat
  - Durum: ✅ Kapatıldı (2025-12-22)

- [x] **Görev:** `tests/test_event_detector.py` satır limiti payı açma
  - Açıklama: Dosya 467 → 314 satır (parametrize ile tekrar azaltma); `standards_auto_check` uyarısı kapatıldı.
  - Öncelik: 3 (Orta/Düşük)
  - Tahmini Süre: 1-2 saat
  - Durum: ✅ Kapatıldı (2025-12-22)

- [x] **Görev:** `tests/test_protocol_rules.py` satır limiti payı açma
  - Açıklama: Dosya 473 → 399 satır; `standards_auto_check` uyarısı kapatıldı.
  - Öncelik: 3 (Orta/Düşük)
  - Tahmini Süre: 1-2 saat
  - Durum: ✅ Kapatıldı (2025-12-22)
  - Test/Doğrulama: `./env/bin/python -m py_compile tests/test_protocol_rules.py` + `./env/bin/pytest -q tests/test_protocol_rules.py` ✅

- [x] **Görev:** `tests/test_integration.py` satır limiti payı açma
  - Açıklama: Dosya 433 → 393 satır; `standards_auto_check` uyarısı kapatıldı.
  - Öncelik: 3 (Orta/Düşük)
  - Tahmini Süre: 30-60 dk
  - Durum: ✅ Kapatıldı (2025-12-22)

- [x] **Görev:** `tests/test_api_endpoints.py` satır limiti payı açma
  - Açıklama: Dosya 464 → 391 satır; `standards_auto_check` uyarısı kapatıldı.
  - Öncelik: 3 (Orta/Düşük)
  - Tahmini Süre: 30-60 dk
  - Durum: ✅ Kapatıldı (2025-12-22)


### Öncelik 1: EV Gerçek Test Bulguları (2025-12-13) - Güç/Enerji Tutarlılığı ve UI Stabilitesi

- [ ] **Görev:** Acrel ADL400 enerji register anlamları (energy_total vs energy_import/export) doğrulaması
  - Açıklama: `/api/meter/reading` içinde `energy_kwh`, `energy_import_kwh`, `energy_export_kwh` alanlarının hangi sayaç register’larından geldiği ve “import”/“total” semantiğinin doğru olduğu sahada teyit edilmeli. Export değeri sabit görünebiliyor (ör. 0.3 kWh) — bu hata olmayabilir, ama register map üzerinden doğrulanmalı.
  - Öncelik: 2 (Orta)
  - Tahmini Süre: 1-2 saat
  - Durum: 🟡 Kısmi (2025-12-14)
  - Not: Yazılım tarafında `api/meter/acrel.py` `totals` içine `energy_total_kwh` alias ve `registers` referans bloğu eklendi. Saha teyidi hâlâ gerekli.

- [ ] **Görev:** `/api/current/available` endpoint’ini kaldırma/deprecate kararı
  - Açıklama: Endpoint şu an statik aralık döndürüyor (6-32). Kullanım yoksa kaldırılabilir; kullanılacaksa station/meter/ESP32 config’e göre dinamik hale getirilebilir.
  - Öncelik: 3 (Orta/Düşük)
  - Tahmini Süre: 0.5-1 saat
  - Durum: 💡 İyileştirme fırsatı

- [x] **Görev:** `api/database/session_queries.py` satır limiti payı açma
  - Açıklama: Dosya 404 → 387 satır; `standards_auto_check` uyarısı kapatıldı.
  - Öncelik: 2 (Orta)
  - Tahmini Süre: 1-2 saat
  - Durum: ✅ Kapatıldı (2025-12-22)

- [x] **Görev:** `api/routers/sessions.py` satır limiti payı açma
  - Açıklama: Dosya 417 → 350 satır; `standards_auto_check` uyarısı kapatıldı.
  - Öncelik: 2 (Orta)
  - Tahmini Süre: 1-2 saat
  - Durum: ✅ Kapatıldı (2025-12-22)

### Faz 1: Temel Altyapı (Kritik) - Devam Ediyor

#### ✅ ESP32-RPi Bridge Modülü

#### ✅ REST API Geliştirme

---

## Faz 2: API Katmanı - Devam Ediyor

### ✅ Test Altyapısı Kurulumu (Tamamlandı - 2025-12-09)
### Öncelik 0: STATE Verileri Yönetimi İyileştirmesi (State Management Expert - Codebase Deep Dive Bulgusu)

#### ✅ STATE Verileri Yönetimi ve Validation - Tamamlandı
### Öncelik 1: API Test İyileştirmeleri (API Testleri Deep Dive Bulgusu)

#### ✅ Eksik Test Senaryoları - Tamamlandı (13:40:00)
#### ✅ Test Dokümantasyonu - Tamamlandı (13:15:00)
### Öncelik 1: Performance İyileştirmeleri (Performance Expert - Codebase Deep Dive Bulgusu)

#### ✅ Response Caching Implementasyonu - Tamamlandı (14:30:00)
#### ✅ Database Query Optimization - Tamamlandı (15:10:00)
### Öncelik 1: Architecture İyileştirmeleri (Architecture Expert - Codebase Deep Dive Bulgusu)

#### ✅ Service Layer Ekleme - Tamamlandı (15:45:00)
### Öncelik 1: Code Quality İyileştirmeleri (Code Quality Expert - Codebase Deep Dive Bulgusu)

### Öncelik 2: Mobil Deneyim İyileştirmeleri

#### 🔄 Mobile API → OCPP/CSMS Map (03:20:00) - Yeni
- [ ] **Görev:** Mobile API response'unu OCPP `MeterValues` / `TransactionEvent` şemasına haritalamak
  - Açıklama: `/api/mobile/charging/*` JSON’ları şu anda proje içi alan isimleriyle hazırlanıyor. CSMS entegrasyonuna hazırlık için `measurements` ve `session` alanlarının OCPP sözlüğüyle birebir eşleştirilmesi gerekiyor (ör. `energy.import.register`, `measurand=Power.Active.Import`, `context=Transaction.Begin/End`).
  - Öncelik: 2 (Yüksek)
  - Tahmini Süre: 3-4 saat
  - Durum: 📋 Bekliyor
  - Detaylar:
    - Response şemasına `ocpp_mappings` bloğu eklenebilir veya alan isimleri doğrudan standartlaştırılabilir.
    - İleride CSMS'ye forward edilecek event'ler için payload normalization gerekecek.
    - `Docs/api_reference.md` ve `project_info` içinde yeni sözlük güncellenmeli.

#### ⚙️ Mobile API Selective Payload / Query Options (03:20:00) - Yeni
- [ ] **Görev:** `/api/mobile/charging/current` için alan seçimi (include/exclude) ve hafifletilmiş mod eklemek
  - Açıklama: Şu an tüm veriler tek payload’da dönüyor (~kilobyte seviyesinde). Mobil ekip sadece belirli bloklara ihtiyaç duyduğunda gereksiz veri transferi oluşuyor.
  - Öncelik: 2 (Yüksek)
  - Tahmini Süre: 2 saat
  - Durum: 📋 Bekliyor
  - Detaylar:
    - `?include=alerts,trend` veya `?lite=true` gibi parametrelerle ölçüm, alert veya trend blokları isteğe bağlı döndürülebilir.
    - Genişleyen payload için caching stratejisi ve rate limiting gözden geçirilmeli.
    - Swagger/Docs güncellenerek mobil geliştiricilere yeni parametreler anlatılmalı.

#### ✅ Code Duplication Azaltma - Tamamlandı (16:00:00)
### Öncelik 1: DevOps İyileştirmeleri (DevOps Expert - Codebase Deep Dive Bulgusu)

#### ✅ Monitoring/Alerting Ekleme - Tamamlandı (18:00:00)
### Öncelik 1: Testing İyileştirmeleri (Testing Expert - Codebase Deep Dive Bulgusu)

#### 🧪 Performance Testleri Ekleme
- [ ] **Görev:** Performance testleri ekleme
  - Açıklama: Codebase deep dive analizi sonucu Testing Expert tarafından tespit edildi. Performance testleri eksik.
  - Öncelik: 1 (Yüksek)
  - Tahmini Süre: 2-3 saat
  - Durum: 🧪 Testing Expert - Performance testleri eksik
  - Detaylar: `reports/CODEBASE_DEEPDIVE_ANALYSIS_20251210.md` dosyasına bakınız
  - İmplementasyon:
    - pytest-benchmark kullanılabilir
    - API endpoint performance testleri
    - Database query performance testleri
  - Durum: 📋 Bekliyor

#### 🧪 Load Testleri Ekleme
- [ ] **Görev:** Load testleri ekleme
  - Açıklama: Codebase deep dive analizi sonucu Testing Expert tarafından tespit edildi. Load testleri eksik.
  - Öncelik: 1 (Yüksek)
  - Tahmini Süre: 2-3 saat
  - Durum: 🧪 Testing Expert - Load testleri eksik
  - Detaylar: `reports/CODEBASE_DEEPDIVE_ANALYSIS_20251210.md` dosyasına bakınız
  - İmplementasyon:
    - Locust veya benzeri tool kullanılabilir
    - Concurrent request testleri
    - Stress testleri
  - Durum: 📋 Bekliyor

### Öncelik 1: State Management İyileştirmeleri (State Management Expert - Codebase Deep Dive Bulgusu)

#### 🔄 State History Tracking Ekleme
- [ ] **Görev:** State history tracking ekleme
  - Açıklama: Codebase deep dive analizi sonucu State Management Expert tarafından tespit edildi. State history tracking eksik.
  - Öncelik: 1 (Yüksek)
  - Tahmini Süre: 2-3 saat
  - Durum: 🔄 State Management Expert - State history tracking eksik
  - Detaylar: `reports/CODEBASE_DEEPDIVE_ANALYSIS_20251210.md` dosyasına bakınız
  - İmplementasyon:
    - State transition history kaydı
    - State duration tracking
    - State history API endpoint'i
  - Durum: 📋 Bekliyor

### Öncelik 1: Communication İyileştirmeleri (Communication Expert - Codebase Deep Dive Bulgusu)

#### ✅ Error Recovery İyileştirmesi - Tamamlandı (18:45:00)
#### ✅ Retry Logic Ekleme - Tamamlandı (18:30:00)
### Öncelik 1: API Security İyileştirmesi (Security Expert - Codebase Deep Dive Bulgusu)

#### ✅ Rate Limiting Implementasyonu - Tamamlandı (13:00:00)
#### 🔒 Session History Endpoint Authentication (Yeni)
- [ ] **Görev:** Geçmiş şarj/session endpoint'lerini authentication ile koru (`/api/sessions/*`, `/api/mobile/charging/sessions*`)
  - Açıklama: Bu endpoint'ler şu an `verify_api_key`/auth dependency kullanmıyor. `user_id` query/path ile farklı kullanıcıların geçmiş session verisi istenebilir (multi-user senaryosunda veri sızıntısı riski).
  - Öncelik: 1 (Yüksek)
  - Tahmini Süre: 1-2 saat
  - Durum: 📋 Bekliyor
  - Detaylar: `verify_api_key` eklenmeli; ayrıca `user_id` erişim yetkilendirmesi (caller ↔ user_id eşleştirmesi) netleştirilmeli.

#### 🔄 API Key Rotation Mekanizması
- [ ] **Görev:** API key rotation mekanizması implementasyonu
  - Açıklama: Codebase deep dive analizi sonucu Security Expert tarafından tespit edildi. API key'lerin periyodik olarak değiştirilmesi için mekanizma eklenmeli.
  - Öncelik: 1 (Yüksek)
  - Tahmini Süre: 2-3 saat
  - Durum: ⏸️ ERTELENDİ - User istediğinde yapılacak
  - Detaylar: `reports/CODEBASE_DEEPDIVE_ANALYSIS_20251210.md` dosyasına bakınız
  - İmplementasyon:
    - Multiple API keys desteği
    - API key expiration mekanizması
    - Graceful rotation (eski key'ler belirli süre geçerli kalır)
    - Key revocation mekanizması
  - **NOT:** Bu görev ertelendi. User istediğinde yapılacak. Gelecekteki analizlerde ignore edilecek.
  - Durum: ⏸️ Ertelendi

#### ✅ CORS Policy Tanımlama - Tamamlandı (13:10:00)
#### ✅ API Key Logging İyileştirmesi - Tamamlandı (18:15:00)
### Öncelik 1: API Authentication İyileştirmesi (Gelecek Faz - JWT/OAuth2)
- [ ] **Görev:** API güvenlik katmanı iyileştirmesi (JWT/OAuth2)
  - Açıklama:
    - Mevcut API key sistemi var ve çalışıyor
    - JWT token veya OAuth2 eklenebilir (gelecek faz için)
  - Öncelik: 1 (Yüksek - Gelecek Faz)
  - Tahmini Süre: 4-6 saat
  - Bağımlılıklar: ✅ Rate limiting, API key rotation (Tamamlandıktan sonra)
  - Notlar: Mevcut API key sistemi yeterli, bu iyileştirme gelecek faz için
  - **NOT:** Bu görev ertelendi. User istediğinde yapılacak. Gelecekteki analizlerde ignore edilecek.
  - Durum: ⏸️ Ertelendi

---

## Faz 3: OCPP Entegrasyonu

### Öncelik 2: OCPP Implementasyonu ve CSMS Entegrasyonu
- [ ] **Görev:** OCPP protokol desteği ve CSMS entegrasyonu
  - Açıklama:
    - OCPP 1.6J: WebSocket bağlantı yönetimi ve temel OCPP mesajları (Authorize, StartTransaction, StopTransaction, StatusNotification)
    - OCPP 2.0.1: OCPP 2.0.1 protokol desteği ve yeni özellikler (çift versiyon desteği)
    - CSMS: Merkezi sistem ile haberleşme (WebSocket üzerinden CSMS bağlantısı)
  - Öncelik: 2 (Yüksek)
  - Tahmini Süre: 4-6 gün (OCPP 1.6J: 1-2 gün, OCPP 2.0.1: 1-2 gün, CSMS: 2-3 gün)
  - Bağımlılıklar: API katmanının stabil olması, OCPP 1.6J implementasyonu (OCPP 2.0.1 için), OCPP implementasyonu (CSMS için)
  - Durum: 📋 Bekliyor

### Öncelik 2: OCPP 1.6J Fallback — Smoke Test (2025-12-21)

- [ ] **Görev:** CSMS Admin UI BasicAuth erişimi (station-side doğrulama için)
  - Açıklama: `https://lixhium.xyz/` admin UI `Basic realm="CSMS Admin UI"` ile korunuyor. Station BasicAuth credentials (ör. `STATION_NAME:password`) UI için geçerli değil. Station AI’ın “stations list / last_seen / connected_at” doğrulaması yapabilmesi için admin kullanıcı/parola sağlanmalı veya UI kontrolü CSMS AI tarafından yapılmalı.
  - Öncelik: 2 (Yüksek - doğrulama/operasyonel ihtiyaç)
  - Tahmini Süre: 10-15 dk
  - Durum: 📋 Bekliyor

- [ ] **Görev:** CSMS API route çakışması: `GET /api/v1/station/pending` unreachable (422)
  - Açıklama: OpenAPI’de `/api/v1/station/pending` tanımlı ancak runtime’da `station_id` path param route’u tarafından gölgeleniyor; çağrı `station_id="pending"` olarak parse edilmeye çalışıp 422 dönüyor. Bu nedenle pending stations listesi/UI doğrulaması bloklanıyor.
  - Öncelik: 1 (Yüksek - CSMS tarafı bug)
  - Tahmini Süre: 15-30 dk
  - Durum: 🧱 Bloklayıcı (CSMS fix gerekli)

- [ ] **Görev:** OCPP WS disconnect (close code=1000) → `connected_ids=[]` ve RemoteStop 404 (operasyonel risk)
  - Açıklama: UI Remote Ops testinde CSMS tarafında “station WS disconnect (code=1000)” ve “message bus connected_ids=[]” gözlendi; bu durumda RemoteStop 404 dönebiliyor. Station daemon reconnect ediyor ancak bağlantı flapping operasyonu zayıflatıyor. Kök neden için CSMS idle timeout / load balancer / app restart / ping-pong davranışı incelenmeli; Station tarafında gerekirse keepalive stratejisi (heartbeat override önerisi, ping interval explicit) dokümante edilmeli.
  - Öncelik: 1 (Yüksek - operasyonel blokaj)
  - Tahmini Süre: 30-90 dk (analiz + dokümantasyon + gerekirse küçük ayar)
  - Durum: ✅ Kapatıldı (false positive: CSMS deploy/restart/CI kaynaklı; CI iyileştirildi)
  - Detaylar:
    - Önce: flapping (code=1000) + arada HTTP 502 görüldü.
    - Retest: CSMS fix sonrası + station `--heartbeat-seconds 60` ile uzun aralıkta stabil; RemoteStart+RemoteStop başarıyla tamamlandı. Uzun pencerede 1 kez code=1000 reconnect görüldü; Master AI bunun CSMS deploy/restart ve (daha önce) doc/todo değişimlerinde restart tetikleyen CI davranışı kaynaklı olabileceğini teyit etti; CI ayarı güncellendi (SSOT: `docs/csms/CSMS_CONNECTION_PARAMETERS.md`).

- [ ] **Görev:** `todo/checkpoint.md` legacy/çelişkili blokları temizle (SSOT netliği)
  - Açıklama: `todo/checkpoint.md` içinde proje başlangıcından kalan eski şablon/progress blokları bulunuyor. SSOT netliği için sadece checkpoint kayıtları kalacak şekilde sadeleştirilmeli (tarihçe korunmalı).
  - Öncelik: 3 (Orta)
  - Tahmini Süre: 15-30 dk
  - Durum: 💡 İyileştirme fırsatı

---

## Faz 4: Meter ve Monitoring

### Öncelik 5: Meter Okuma Modülü Geliştirme
- [ ] **Görev:** Meter okuma modülü geliştir (`meter/read_meter.py`)
  - Açıklama: Enerji ölçüm cihazı entegrasyonu (Meter abstraction layer mevcut, fiziksel test bekliyor)
  - Öncelik: 5 (Orta)
  - Tahmini Süre: 1-2 gün
  - Notlar: Veri toplama ve işleme, fiziksel bağlantı testi gerekli
  - Durum: 📋 Bekliyor

### Öncelik 5: Monitoring ve Logging İyileştirme
- [ ] **Görev:** Sistem durumu izleme ve logging iyileştirmesi
  - Açıklama: Hata loglama ve performans metrikleri (Logging sistemi mevcut)
  - Öncelik: 5 (Orta)
  - Tahmini Süre: 1 gün
  - Notlar: Monitoring dashboard eklenebilir
  - Durum: 📋 Bekliyor

---

## Faz 5: Test ve Optimizasyon

### Öncelik 3: Test Suite Genişletme (Testing Expert - Codebase Deep Dive Bulgusu)
- [ ] **Görev:** Unit testler ve entegrasyon testleri genişletme
  - Açıklama: Codebase deep dive analizi sonucu Testing Expert tarafından tespit edildi. Test coverage ~70%, %90+ hedefi. ESP32-RPi iletişim testleri, OCPP protokol testleri (Test altyapısı mevcut, coverage %84)
  - Öncelik: 1 (Yüksek)
  - Tahmini Süre: 2-3 gün
  - Durum: 🧪 Testing Expert - Test coverage artırılmalı (%90+ hedef)
  - Detaylar: `reports/CODEBASE_DEEPDIVE_ANALYSIS_20251210.md` dosyasına bakınız
  - Notlar: pytest kullanılabilir, coverage %90+ hedefi
  - Durum: 📋 Bekliyor

---

## Faz 6: Loglama ve Session Yönetimi (Devam Ediyor - 2025-12-09)

### ✅ Temel Loglama Sistemi (Tamamlandı - 2025-12-09)
### ✅ Event Detection Modülü (Tamamlandı - 2025-12-09)
### Öncelik 2: Gerçek Araç SOC Limiti İçin Kullanıcı Uyarısı (2025-12-11)
- [ ] **Görev:** READY durumunda uzun süre akım yoksa SOC limiti uyarısı üret
  - Açıklama: Gerçek araç testinde, araç BMS SOC limiti %60 iken READY durumunda olmasına rağmen şarjı başlatmadı; istasyon tarafı doğru davrandı ancak kullanıcı tecrübesi karışık oldu. READY/EV_CONNECTED state uzun süre devam edip akım çekilmiyorsa, araçta SOC limiti veya benzeri bir kısıt olabileceğine dair API/web arayüzü üzerinden açıklayıcı uyarı gösterilmeli.
  - Öncelik: 2 (Yüksek - UX İyileştirme)
  - Tahmini Süre: 2-3 saat
  - Durum: 💡 İyileştirme fırsatı
  - Detaylar: `docs/REAL_VEHICLE_TEST_CHECKLIST.md` ve `project_info_20251208_145614.md` içindeki 2025-12-11 gerçek araç senaryosu özetine bakınız.
  - Durum: 📋 Bekliyor

### Öncelik 3: Session Summary Generation
- [ ] **Görev:** Session summary generator oluştur
  - Açıklama: Session özeti hesaplama, istatistikler, rapor oluşturma
  - Öncelik: 3 (Orta)
  - Tahmini Süre: 2-3 gün
  - Bağımlılıklar: ✅ Session manager (Tamamlandı)
  - Notlar: Enerji, akım, süre, state duration'ları
  - İyileştirme Fırsatları:
    - Real-time summary updates
    - Summary caching
    - Export functionality (CSV, JSON, PDF)
  - Durum: 📋 Bekliyor

### Öncelik 4: Session API Endpoint'leri İyileştirme
- [ ] **Görev:** Session API endpoint'leri iyileştirme
  - Açıklama: Mevcut endpoint'lere ek özellikler (`GET /api/sessions/{id}/summary`, filtering, sorting)
  - Öncelik: 4 (Orta)
  - Tahmini Süre: 1-2 gün
  - Bağımlılıklar: ✅ Session manager (Tamamlandı)
  - Notlar: RESTful API tasarımı, mevcut endpoint'ler var (GET /api/sessions, GET /api/sessions/{id}, GET /api/sessions/current, GET /api/sessions/count/stats, GET /api/sessions/{id}/metrics, GET /api/sessions/stats/energy, GET /api/sessions/stats/power, GET /api/users/{user_id}/sessions)
  - İyileştirme Fırsatları:
    - Pagination support (mevcut)
    - Filtering ve sorting (kısmen mevcut)
    - API versioning
    - GET /api/sessions/{id}/summary endpoint'i ekleme
  - Durum: 📋 Bekliyor

---

## Faz 7: Code Quality ve DevOps İyileştirmeleri (Yeni - 2025-12-09)

### Öncelik 0: Kod ve Dokümantasyon Standartlarına Uyum

#### 🔴 KRİTİK: Standart İhlalleri (Standart Kontrol Raporu - 2025-12-10)

##### 🔴 Maksimum Sınır Aşıldı (Acil Refactor Gerekli)
- [ ] **Görev:** `api/database` paketinde standart uyumu → ✅ Tamamlandı (2025-12-10 21:24)
  - Açıklama: Eski 656 satırlık `api/database/queries.py` dosyası konu bazlı mixin'lere bölündü; fonksiyon uzunlukları ve dosya boyutları limitlerin altına çekildi.
  - Öncelik: 0 (Acil)
  - Tahmini Süre: 4-6 saat
  - Durum: ✅ Tamamlandı
  - Detaylar: `scripts/standards_auto_check.py` raporuna bakınız
  - Son Yapı:
    - `api/database/core.py` - Core database operations (427 satır, uyarı eşiğinde)
    - `api/database/migrations.py` - Migration operations
    - `api/database/session_queries.py`, `event_queries.py`, `maintenance_queries.py` - Query mixin'leri
    - `api/database/queries.py` - Mixin agregasyonu (20 satır)
    - `api/database/models.py` - Database models

#### 🔴 KRİTİK: Workspace Boyutu (Workspace Kontrol Raporu - 2025-12-10)
#### ✅ State Değerleri Standardizasyonu (API Testleri Deep Dive Bulgusu) - Tamamlandı
#### ✅ Mock Yapısı Standardizasyonu - Tamamlandı
- [ ] **Görev:** `MULTI_EXPERT_ANALYSIS.md` bölümleme
  - Açıklama: Uyarı eşiği (1000 satır) aşıldı (1115 satır). Bölümlere ayırılabilir
  - Öncelik: 4 (Orta)
  - Tahmini Süre: 1-2 saat
  - Durum: 🟡 Uyarı eşiği aşıldı
  - Detaylar: `todo/REFACTORING_PLAN.md` dosyasına bakınız
  - Durum: 📋 Bekliyor

- [x] **Görev:** `meter/read_meter.py` kompaktlaştırma (satır limiti payı)
  - Açıklama: Dosya 497 satırdan 410 satıra indirildi; 500 limitine “yakın” riski kapatıldı (docstring kısaltma + ortak register okuma helper’ı).
  - Öncelik: 6 (Düşük)
  - Tahmini Süre: 2-3 saat
  - Durum: ✅ Kapatıldı (2025-12-22)
  - Detaylar: `todo/REFACTORING_PLAN.md` dosyasına bakınız
  - Test/Doğrulama: `./env/bin/python -m py_compile meter/read_meter.py` + `./env/bin/pytest -q tests/test_api_endpoints.py` ✅


### Öncelik 6: Code Quality Tools Kurulumu
- [ ] **Görev:** Code quality tools kurulumu
  - Açıklama: Black (formatter) ve Ruff (linter) kurulu, Mypy (type checker) ve pre-commit hooks iyileştirmesi
  - Öncelik: 6 (Düşük)
  - Tahmini Süre: 1-2 saat
  - İyileştirme Fırsatları:
    - Automated code quality checks (kısmen mevcut)
    - CI/CD pipeline'a entegrasyon
    - Code quality metrics tracking
  - Durum: 📋 Bekliyor

### Öncelik 7: CI/CD Pipeline Kurulumu (DevOps Expert - Codebase Deep Dive Bulgusu)
- [ ] **Görev:** CI/CD pipeline kurulumu
  - Açıklama: Codebase deep dive analizi sonucu DevOps Expert tarafından tespit edildi. CI/CD pipeline eksik. GitHub Actions workflow, automated testing, automated linting, deployment automation.
  - Öncelik: 1 (Yüksek)
  - Tahmini Süre: 2-3 saat
  - Durum: 🚀 DevOps Expert - CI/CD pipeline eksik
  - Detaylar: `reports/CODEBASE_DEEPDIVE_ANALYSIS_20251210.md` dosyasına bakınız
  - İmplementasyon:
    - GitHub Actions workflow
    - Automated testing pipeline
    - Automated linting
    - Deployment automation
  - İyileştirme Fırsatları:
    - Multi-environment deployment (dev/staging/prod)
    - Automated security scanning
    - Performance regression testing
  - Durum: 📋 Bekliyor

---

## Faz 4: Meter ve Monitoring (Devam Ediyor)


---

## Audit Bulguları (2025-12-10)

### 🔴 Kritik Sorunlar (Acil Müdahale Gerekli)

#### ✅ Test Dosyası Refactoring (Tamamlandı)
### 🟡 Uyarılar (Yakında Çözülmeli)

#### Öncelik 3: Test Dosyaları Refactoring (Orta)
- [ ] **Görev:** Test dosyaları refactoring
  - Açıklama: 2 test dosyası uyarı eşiğinde
    - `tests/test_additional_edge_cases.py`: 471 satır (Limit: 500)
    - `tests/test_api_edge_cases.py`: 476 satır (Limit: 500)
  - Öncelik: 3 (Orta)
  - Tahmini Süre: 2-4 saat (her biri için 1-2 saat)
  - Durum: 🟡 Uyarı eşiği yakın
  - Aksiyon: Test suite'lere bölünmeli
  - Detaylar: `docs/AUDIT_REPORT_20251210.md` dosyasına bakınız

#### Öncelik 5: Workspace Temizliği (Düşük)
- [ ] **Görev:** Workspace temizliği
  - Açıklama: Workspace boyutu 81.75 MB (İdeal: < 80 MB) - uyarı eşiğinde
  - Öncelik: 5 (Düşük)
  - Tahmini Süre: 1 saat
  - Durum: 🟡 Uyarı eşiğinde
  - Aksiyon: Log dosyaları kontrol edilmeli, gereksiz dosyalar temizlenmeli
  - Detaylar: `docs/AUDIT_REPORT_20251210.md` dosyasına bakınız

### 🟢 Opsiyonel İyileştirmeler

#### Öncelik 7: Kod Kalitesi Araçları (Opsiyonel)
- [ ] **Görev:** Kod kalitesi araçları kurulumu
  - Açıklama: Black formatter ve Ruff linter kurulu değil (opsiyonel)
  - Öncelik: 7 (Opsiyonel)
  - Tahmini Süre: 2-3 saat
  - Durum: 🟢 Opsiyonel
  - Aksiyon: Black ve Ruff kurulumu, pre-commit hook'larına entegrasyon
  - Detaylar: `docs/AUDIT_REPORT_20251210.md` dosyasına bakınız

---

## Genel Notlar

- Görevler öncelik sırasına göre sıralanmıştır (Öncelik 0: Acil → Öncelik 8: Düşük)
- Her görev tamamlandığında `master_done.md`'ye taşınacak
- Aktif görevler `master_live.md`'ye taşınacak
- Görevler proje planlamasına göre fazlara ayrılmıştır
- **Öncelik Sistemi:** Detaylar için `todo/PRIORITY_SYSTEM_STANDARD.md` dosyasına bakınız
- **Yeni:** Loglama ve Session Yönetimi fazı eklendi (2025-12-09)
- **Yeni:** Code Quality ve DevOps İyileştirmeleri fazı eklendi (2025-12-09)
- **Yeni:** Audit bulguları eklendi (2025-12-10)
- **Güncelleme:** Genel durum değerlendirmesi ve iyileştirme fırsatları analizi yapıldı (2025-12-09 21:35:00)
- **Güncelleme:** Kod ve dokümantasyon standartlarına uyum görevleri eklendi (2025-12-09 22:15:00)
- **Güncelleme:** Event Detection tamamlandı bilgisi güncellendi, api/main.py önceliği acil olarak işaretlendi (2025-12-10 02:10:00)
- **Güncelleme:** Genel audit raporu eklendi, audit bulguları master_next.md'ye eklendi (2025-12-10 01:35:00)
- **Güncelleme:** Workspace reorganizasyonu tamamlandı (2025-12-10 02:00:00)
- **Güncelleme:** Session Management audit raporu eklendi (2025-12-10 04:20:00)
- **Güncelleme:** Session Management deep dive analizi eklendi (2025-12-10 05:30:00)
- **Güncelleme:** Database deep dive analizi eklendi (2025-12-10 06:00:00)
- **Güncelleme:** Todo dosyaları deep dive analizi ve temizlik yapıldı (2025-12-10 09:30:00)
- **Güncelleme:** Öncelik sistemi standardize edildi (2025-12-10 09:35:00)

---

## Database Deep Dive Analizi Bulguları (2025-12-10)

### 🔴 Kritik Database Sorunları (Acil Müdahale Gerekli)


---

## Session Management Audit Bulguları (2025-12-10)

### 🟢 Genel Durum: Çok İyi (Skor: 9.0/10)

Session Management modülü başarıyla implement edildi. Kod kalitesi yüksek, test coverage iyi, mimari uyum mükemmel.

### 🟡 İyileştirme Fırsatları (Orta Öncelik)


### Öncelik 4: Test Dosyası Refactoring
- [ ] **Görev:** `tests/test_session_manager.py` test suite'lere bölme
  - Açıklama: Dosya boyutu 368 satır (Uyarı: 400) - uyarı eşiğinde. Test suite'lere bölünebilir
  - Öncelik: 4 (Orta)
  - Tahmini Süre: 1 saat
  - Durum: 🟡 Uyarı eşiği yakın
  - Önerilen Yapı:
    - `tests/session/test_session.py` - ChargingSession testleri
    - `tests/session/test_manager.py` - SessionManager testleri
    - `tests/session/test_integration.py` - Integration testleri
  - Detaylar: `docs/SESSION_MANAGEMENT_AUDIT_20251210.md` dosyasına bakınız
  - Durum: 📋 Bekliyor

### 🟢 Gelecek Faz İyileştirmeleri (Düşük Öncelik)

### Öncelik 6: Session Analytics (Gelecek Faz)
- [ ] **Görev:** Session analytics ve reporting özellikleri
  - Açıklama: Session süresi analizi, enerji tüketimi analizi, fault analizi (Database entegrasyonu mevcut)
  - Öncelik: 6 (Düşük)
  - Tahmini Süre: 2-3 gün
  - Durum: 🟢 Gelecek faz
  - Detaylar: `docs/SESSION_MANAGEMENT_AUDIT_20251210.md` dosyasına bakınız
  - Durum: 📋 Bekliyor

---

## Şarj Metrikleri Analizi Bulguları (2025-12-10)

### 🔴 Kritik Eksiklik: Şarj Metrikleri Yok

**Kullanıcı Geri Bildirimi:** "Şarj ile ilgili, süre, şarj sonu tüketilen enerji miktarı, şarj esnasındaki maksimum güç, vb. başka bilgiler hem session sırasında hem de session sonunda önemli değil mi?"

**Mevcut Durum:** 🔴 Kritik metrikler eksik

### 🔴 Kritik Eksik Metrikler


### 📊 Önerilen Database Şeması (Metriklerle)

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    start_time INTEGER NOT NULL,
    end_time INTEGER,
    status TEXT NOT NULL,

    -- Süre metrikleri
    duration_seconds INTEGER,
    charging_duration_seconds INTEGER,
    idle_duration_seconds INTEGER,

    -- Enerji metrikleri
    total_energy_kwh REAL,
    start_energy_kwh REAL,
    end_energy_kwh REAL,

    -- Güç metrikleri
    max_power_kw REAL,
    avg_power_kw REAL,
    min_power_kw REAL,

    -- Akım metrikleri
    max_current_a REAL,
    avg_current_a REAL,
    min_current_a REAL,
    set_current_a REAL,

    -- Voltaj metrikleri
    max_voltage_v REAL,
    avg_voltage_v REAL,
    min_voltage_v REAL,

    -- Diğer alanlar
    event_count INTEGER DEFAULT 0,
    events TEXT NOT NULL DEFAULT '[]',
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
)
```

**Detaylar:** `docs/SESSION_CHARGING_METRICS_ANALYSIS_20251210.md` dosyasına bakınız

---

## Öncelik 8: Sistem İyileştirmeleri (Düşük Öncelik)

### Workspace Temizliği ve Optimizasyonu

- [ ] **Görev:** Workspace temizliği
  - Açıklama: Workspace boyutu (env/logs hariç) ~30 MB; env/ ~98.55 MB, logs/ ~95 MB. Cihazda disk kullanımını izlemek için periyodik temizlik/optimizasyon planlanmalı (özellikle logs/ rotasyon/retention).
  - Öncelik: 8
  - Tahmini Süre: 30 dakika
  - Durum: 📋 Bekliyor
  - Detaylar: `scripts/workspace_auto_check.py` raporuna bakınız
  - Aksiyon (2025-12-12 21:05:00): `docs/acrel/` klasörü `.gitignore`'a eklenerek ağır görsel/doküman arşivi git geçmişinden hariç tutuldu. Durum: ✅ 2025-12-12 21:12:00 (Code Quality Expert)
  - Not (2025-12-22): Kök dizin kontrol edildi; `3}s` adlı beklenmedik dosya şu an görünmüyor (muhtemelen otomatik/manuel temizlendi).

- [ ] **Görev:** Bazı session'larda enerji delta/başlangıç zamanı plausibility analizi (SKIP edilenler)
  - Açıklama: Retro metrik düzeltme sırasında bazı kayıtlar `energy_kwh` değeri, teorik maksimuma göre imkânsız çıktığı için otomatik düzeltilmedi (muhtemel sayaç reset/rollover, register semantiği veya timestamp (ms/s) hatası). Bu kayıtlar ayrıca start_time sıralamasını bozabilir.
  - Öncelik: 2 (Orta)
  - Tahmini Süre: 1-2 saat
  - Durum: 📋 Bekliyor

- [ ] **Görev:** HTTP caching (ETag/304) saha ölçümü ve TTL optimizasyonu
  - Açıklama: Browser/ngrok gibi dış client’larda `ETag`/`304 Not Modified` oranı ve bandwidth kazanımı ölçülmeli. Ölçüme göre TTL’ler sahaya uygun ayarlanmalı (örn. `/api/status` 5s, `/api/health` 30s, `/api/sessions/current` 10s, `/api/mobile/charging/current` 5-10s).
  - Öncelik: 2 (Orta)
  - Tahmini Süre: 30-60 dakika
  - Durum: 📋 Bekliyor

- [ ] **Görev:** Session metadata’ya `meter_type` (abb/acrel/mock) yaz (ayırt edilebilirlik)
  - Açıklama: Gelecekte “ABB dönemi / Acrel dönemi” gibi filtrelemeler için session create/end sırasında `metadata.meter_type` kaydı tutulmalı. Böylece temizlik/analiz scriptleri tarih varsayımı yerine güvenilir etiketle çalışır.
  - Öncelik: 3 (Orta)
  - Tahmini Süre: 30-45 dakika
  - Durum: 📋 Bekliyor

- [ ] **Görev:** Session “data quality guard” (anormal metrikleri işaretle)
  - Açıklama: Eğer meter yoksa veya metrikler fiziksel sınırları aşıyorsa (ör. `avg_voltage_v>500` / `avg_power_kw>max_power_kw` gibi) session `metadata.metrics_quality="suspect"` ve `metadata.metrics_quality_reason=[...]` ile işaretlenmeli; UI/trend hesaplarında bu kayıtlar opsiyonel dışlanabilir.
  - Öncelik: 3 (Orta)
  - Tahmini Süre: 45-90 dakika
  - Durum: 📋 Bekliyor

### Database İyileştirmeleri

- [ ] **Görev:** Eski session'lar için user_id migration
  - Açıklama: 105 adet eski session'da user_id yok. Bu session'lar user_id özelliği eklenmeden önceki session'lar. Migration yapılabilir ama kritik değil.
  - Öncelik: 8
  - Tahmini Süre: 1-2 saat
  - Durum: 📋 Bekliyor
  - Not: Yeni session'larda user_id var ✅

- [ ] **Görev:** Test session'larını temizleme
  - Açıklama: 2 adet test session'da events yok (CANCELLED status). Bu session'lar test amaçlı oluşturulmuş olabilir.
  - Öncelik: 8
  - Tahmini Süre: 15 dakika
  - Durum: 📋 Bekliyor

- [ ] **Görev:** DB bakım adımı: VACUUM/ANALYZE (silme sonrası dosya boyutu)
  - Açıklama: ABB dönemindeki session temizliği sonrası SQLite dosya boyutu fiziksel olarak küçülmeyebilir. Bakım komutu olarak `VACUUM` (opsiyonel `ANALYZE`) uygulanmalı; bakım penceresinde çalıştırılmalı.
  - Öncelik: 8
  - Tahmini Süre: 10-20 dakika
  - Durum: 📋 Bekliyor

