# Sonraki Yapılacaklar

**Son Güncelleme:** 2025-12-08 18:30:00

**Not:** Detaylı kıdemli uzman önerileri için `expert_recommendations.md` dosyasına bakınız.

---

## Öncelikli Görevler

### Faz 1: Temel Altyapı (Kritik) - Devam Ediyor

#### ✅ ESP32-RPi Bridge Modülü
- [x] **Tamamlandı:** `esp32/bridge.py` oluşturuldu
- [x] **Tamamlandı:** Protokol tanımları JSON'a eklendi
- [x] **Tamamlandı:** Serial iletişim implementasyonu
- [x] **Tamamlandı:** Durum izleme mekanizması

#### ✅ REST API Geliştirme
- [x] **Tamamlandı:** FastAPI uygulaması oluşturuldu
- [x] **Tamamlandı:** Temel endpoint'ler implement edildi
- [x] **Tamamlandı:** API dokümantasyonu eklendi

---

## Faz 2: API Katmanı - Devam Ediyor

### 🔄 Test Altyapısı Kurulumu (Kritik) - Aktif Görev
- [x] **Aktif:** `master_live.md`'ye taşındı
- [ ] **Görev:** Test altyapısı kurulumu
  - Açıklama: pytest kurulumu, test yapısı oluşturma, ilk testler
  - Öncelik: Kritik
  - Tahmini Süre: 2-3 saat
  - Durum: 🔄 Devam Ediyor (master_live.md'de)

### 🔄 API Test ve İyileştirme
- [ ] **Görev:** API endpoint'lerini test et
  - Açıklama: Tüm API endpoint'lerini gerçek ESP32 ile test et
  - Öncelik: Yüksek
  - Tahmini Süre: 1-2 saat
  - Bağımlılıklar: ESP32 bağlantısı, Test altyapısı kurulumu
  - Notlar: ESP32'nin `/dev/ttyUSB0` portunda olduğundan emin ol

### 🔄 API Hata Yönetimi İyileştirme
- [ ] **Görev:** API hata yönetimini iyileştir
  - Açıklama: Daha detaylı hata mesajları ve logging ekle
  - Öncelik: Orta
  - Tahmini Süre: 1 saat
  - Notlar: Logging sistemi eklenebilir

### 🔄 API Authentication/Authorization
- [ ] **Görev:** API için authentication ekle
  - Açıklama: API endpoint'lerine güvenlik katmanı ekle
  - Öncelik: Orta
  - Tahmini Süre: 2-3 saat
  - Notlar: API key veya JWT token kullanılabilir

---

## Faz 3: OCPP Entegrasyonu

### 📋 OCPP 1.6J Implementasyonu
- [ ] **Görev:** OCPP 1.6J protokol desteği ekle
  - Açıklama: WebSocket bağlantı yönetimi ve temel OCPP mesajları
  - Öncelik: Yüksek
  - Tahmini Süre: 1-2 gün
  - Bağımlılıklar: API katmanının stabil olması
  - Notlar: Authorize, StartTransaction, StopTransaction, StatusNotification mesajları

### 📋 OCPP 2.0.1 Implementasyonu
- [ ] **Görev:** OCPP 2.0.1 protokol desteği ekle
  - Açıklama: OCPP 2.0.1 protokol desteği ve yeni özellikler
  - Öncelik: Yüksek
  - Tahmini Süre: 1-2 gün
  - Bağımlılıklar: OCPP 1.6J implementasyonu
  - Notlar: Çift versiyon desteği sağlanmalı

### 📋 CSMS Entegrasyonu
- [ ] **Görev:** CSMS (Central System Management System) entegrasyonu
  - Açıklama: Merkezi sistem ile haberleşme
  - Öncelik: Yüksek
  - Tahmini Süre: 2-3 gün
  - Bağımlılıklar: OCPP implementasyonu
  - Notlar: WebSocket üzerinden CSMS bağlantısı

---

## Faz 4: Meter ve Monitoring

### 📋 Meter Okuma Modülü
- [ ] **Görev:** Meter okuma modülü geliştir (`meter/read_meter.py`)
  - Açıklama: Enerji ölçüm cihazı entegrasyonu
  - Öncelik: Orta
  - Tahmini Süre: 1-2 gün
  - Notlar: Veri toplama ve işleme

### 📋 Monitoring ve Logging
- [ ] **Görev:** Sistem durumu izleme ve logging
  - Açıklama: Hata loglama ve performans metrikleri
  - Öncelik: Orta
  - Tahmini Süre: 1 gün
  - Notlar: Logging sistemi ve monitoring dashboard

---

## Faz 5: Test ve Optimizasyon

### 📋 Test Suite
- [ ] **Görev:** Unit testler ve entegrasyon testleri
  - Açıklama: ESP32-RPi iletişim testleri, OCPP protokol testleri
  - Öncelik: Yüksek
  - Tahmini Süre: 2-3 gün
  - Notlar: pytest kullanılabilir

### 📋 Dokümantasyon ve Deployment
- [ ] **Görev:** API dokümantasyonu ve kurulum kılavuzu
  - Açıklama: Sistem mimarisi dokümantasyonu ve deployment guide
  - Öncelik: Orta
  - Tahmini Süre: 1 gün
  - Notlar: README.md ve deployment dokümantasyonu

---

## Faz 6: Loglama ve Session Yönetimi (Yeni - 2025-12-09)

### 📋 Temel Loglama Sistemi (Yüksek Öncelik)
- [ ] **Görev:** Logging modülü oluştur (`api/logging.py`)
  - Açıklama: Structured logging (JSON format), log rotation, thread-safe
  - Öncelik: Yüksek
  - Tahmini Süre: 1-2 gün
  - Notlar: ESP32 mesajlarını ve API isteklerini logla

### 📋 Event Detection (Yüksek Öncelik)
- [ ] **Görev:** Event detector oluştur (`api/event_detector.py`)
  - Açıklama: State transition detection, event type classification
  - Öncelik: Yüksek
  - Tahmini Süre: 2-3 gün
  - Bağımlılıklar: Logging modülü
  - Notlar: Kablo takılma, araç bağlantı, şarj başlatma/durdurma event'leri

### 📋 Session Management (Orta Öncelik)
- [ ] **Görev:** Session manager oluştur (`api/session_manager.py`)
  - Açıklama: Session oluşturma, event tracking, session storage
  - Öncelik: Orta
  - Tahmini Süre: 3-4 gün
  - Bağımlılıklar: Event detector, Logging modülü
  - Notlar: Session ID (UUID), başlangıç/bitiş zamanları, event tracking

### 📋 Session Summary Generation (Orta Öncelik)
- [ ] **Görev:** Session summary generator oluştur
  - Açıklama: Session özeti hesaplama, istatistikler, rapor oluşturma
  - Öncelik: Orta
  - Tahmini Süre: 2-3 gün
  - Bağımlılıklar: Session manager
  - Notlar: Enerji, akım, süre, state duration'ları

### 📋 API Endpoint'leri (Orta Öncelik)
- [ ] **Görev:** Session API endpoint'leri ekle
  - Açıklama: `GET /api/sessions`, `GET /api/sessions/{id}`, `GET /api/sessions/current`, `GET /api/sessions/{id}/summary`
  - Öncelik: Orta
  - Tahmini Süre: 1-2 gün
  - Bağımlılıklar: Session manager
  - Notlar: RESTful API tasarımı

---

## Genel Notlar

- Görevler öncelik sırasına göre sıralanmıştır
- Her görev tamamlandığında `master_done.md`'ye taşınacak
- Aktif görevler `master_live.md`'ye taşınacak
- Görevler proje planlamasına göre fazlara ayrılmıştır
- **Yeni:** Loglama ve Session Yönetimi fazı eklendi (2025-12-09)

