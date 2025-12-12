# AC Charger Project

**Proje Tipi:** AC Charger (Elektrikli Araç Şarj İstasyonu)
**Platform:** Raspberry Pi + ESP32
**Dil:** Python (FastAPI) + Arduino (ESP32)
**Repository:** https://github.com/CaiserSz/orge1.git

---

## 🚀 Hızlı Başlangıç

### Projeye Devam Etmek İçin

**AI Asistanları ve Geliştiriciler için:**

```bash
# 1. Projenin durumunu öğren
cat todo/START_HERE.md

# 2. Nerede kaldık?
cat todo/checkpoint.md

# 3. Detaylı durum
cat todo/project_state.md
```

**ÖNEMLİ:** Yeni bir chat oturumunda "projeye devam et" dediğinizde, AI asistanı otomatik olarak:
1. ✅ [`todo/START_HERE.md`](todo/START_HERE.md) dosyasını okuyacak
2. ✅ [`todo/checkpoint.md`](todo/checkpoint.md) ile nerede kaldığını tespit edecek
3. ✅ [`todo/master_next.md`](todo/master_next.md) ile bekleyen görevleri görecek
4. ✅ En yüksek öncelikli görevi seçecek
5. ✅ Proaktif çalışarak projeyi ilerletecek

**Detaylı bilgiler için:** [`todo/PROJECT_CONTINUATION_GUIDE.md`](todo/PROJECT_CONTINUATION_GUIDE.md) ve [`docs/DOCUMENTATION_STRATEGY.md`](docs/DOCUMENTATION_STRATEGY.md)

---

## ✨ Yeni Özellikler (2025-12-09)

### API Authentication
- ✅ Basit API key authentication (`X-API-Key` header)
- ✅ Protected endpoints: `/api/charge/start`, `/api/charge/stop`, `/api/maxcurrent`
- ✅ User tracking (`TEST_API_USER_ID`)
- ✅ Production güvenlik kontrolleri (`ENVIRONMENT` kontrolü)

### API Test Web Sayfası
- ✅ Modern responsive web arayüzü (`/test`)
- ✅ Tüm endpoint'ler için test butonları
- ✅ Request/response body görüntüleme (JSON format)
- ✅ Edit edilebilir cURL komut önizleme
- ✅ Auto API key loading
- ✅ Debounce optimizasyonu (300ms)

### Security Audit ve İyileştirmeler
- ✅ Kapsamlı security audit (güvenlik skoru: 6/10 → 8/10)
- ✅ API key exposure riski düzeltildi
- ✅ Shell command injection koruması
- ✅ Input validation enhancement
- ✅ Error message improvement

### Structured Logging Sistemi
- ✅ JSON formatında structured logging
- ✅ Log rotation (10MB, 5 yedek dosya)
- ✅ Thread-safe logging mekanizması
- ✅ ESP32 mesajları loglanıyor (tx/rx, komutlar, status)
- ✅ API istekleri loglanıyor (middleware ile otomatik, `X-Request-ID` header’ı)
- ✅ Session snapshot/incident logları (`logs/session.log`, `logs/incident.log`)
- ✅ 5 ayrı log dosyası: `logs/api.log`, `logs/esp32.log`, `logs/system.log`, `logs/session.log`, `logs/incident.log`

### Kod Kalitesi İyileştirmeleri
- ✅ Singleton pattern thread-safety (double-check locking)
- ✅ Dependency injection pattern (FastAPI Depends)
- ✅ Robust error handling (monitor loop exception handling)
- ✅ Security hardening (exception handler information leakage düzeltildi)

### Test Altyapısı
- ✅ pytest kurulumu ve yapılandırması
- ✅ 8 test dosyası (~70% coverage)
- ✅ Unit testler, integration testler, thread safety testleri

**Detaylı Bilgi:** `AUDIT_REPORT_20251209.md`, `LOGGING_AUDIT.md`, `PRE_LOGGING_AUDIT.md`

---

## 📁 Proje Yapısı

```
/home/basar/charger/
├── api/                    # REST API (FastAPI)
│   ├── main.py            # Ana API uygulaması
│   └── station_info.py    # İstasyon bilgileri yönetimi
├── esp32/                  # ESP32 Bridge ve Protokol
│   ├── bridge.py           # ESP32 seri iletişim modülü
│   ├── protocol.json       # Protokol tanımları
│   └── Commercial_08122025.ino  # ESP32 firmware
├── ocpp/                   # OCPP Implementasyonu (gelecek)
│   ├── main.py
│   ├── handlers.py
│   └── states.py
├── meter/                  # Meter Okuma Modülü (gelecek)
│   └── read_meter.py
├── data/                   # Veri dosyaları
│   └── station_info.json   # İstasyon bilgileri
├── logs/                   # Log dosyaları
│   ├── meter.log
│   └── system.log
├── todo/                   # Proje Yönetimi ve Todo Sistemi
│   ├── START_HERE.md      # ⚡ BAŞLANGIÇ NOKTASI
│   ├── checkpoint.md       # Nerede kaldık?
│   ├── project_state.md   # Detaylı durum
│   ├── ai_workflow.md     # AI çalışma akışı
│   ├── master.md          # Genel bilgiler ve kurallar
│   ├── master_next.md     # Bekleyen görevler
│   ├── master_live.md     # Aktif görevler
│   ├── master_done.md     # Tamamlanan görevler
│   └── expert_recommendations.md  # Best practices
├── env/                    # Python virtual environment (gitignore)
├── project_info_20251208_145614.md  # Ana proje dokümantasyonu
├── API_EXAMPLES.md         # API kullanım örnekleri
├── station_form.html       # İstasyon bilgileri formu
├── .cursorrules            # Cursor AI kuralları
├── .env                    # Ortam değişkenleri (gitignore)
├── requirements.txt        # Python bağımlılıkları
└── ngrok.yml              # Ngrok yapılandırması
```

---

## 🎯 Proje Durumu

**Güncel durum için:**
- **Hızlı Durum:** [`todo/checkpoint.md`](todo/checkpoint.md)
- **Detaylı Durum:** [`todo/project_state.md`](todo/project_state.md)
- **Bekleyen Görevler:** [`todo/master_next.md`](todo/master_next.md)
- **Aktif Görevler:** [`todo/master_live.md`](todo/master_live.md)

---

## 🔧 Teknik Detaylar

**Detaylı bilgiler için:**
- **Kurulum ve Deployment:** [Deployment Kılavuzu](docs/deployment.md)
- **API Referansı:** [API Referansı](docs/api_reference.md)
- **API Örnekleri:** [API Örnekleri](docs/api_examples.md)
- **Sistem Mimarisi:** [Sistem Mimarisi](docs/architecture.md)

---

## 📚 Dokümantasyon

**Dokümantasyon Stratejisi:** [Single Source of Truth & Multi-Expert Stratejisi](docs/DOCUMENTATION_STRATEGY.md)

### Ana Dokümantasyon (Single Source of Truth)

| Konu | Tek Kaynak | Açıklama |
|------|------------|----------|
| **Kurallar** | [`.cursorrules`](.cursorrules) | Tüm proje kuralları ve agent prensipleri |
| **Proje Bilgileri** | [`project_info_20251208_145614.md`](project_info_20251208_145614.md) | Tüm teknik detaylar, protokol bilgileri |
| **Başlangıç** | [`todo/START_HERE.md`](todo/START_HERE.md) | AI asistanları için başlangıç noktası |
| **Sistem Mimarisi** | [`docs/architecture.md`](docs/architecture.md) | Sistem mimarisi ve modül yapısı |
| **API Referansı** | [`docs/api_reference.md`](docs/api_reference.md) | Tüm API endpoint'leri ve detayları |
| **Deployment** | [`docs/deployment.md`](docs/deployment.md) | Kurulum ve yapılandırma |
| **Sorun Giderme** | [`docs/troubleshooting.md`](docs/troubleshooting.md) | Sorun giderme rehberi |

### Referans Dokümantasyon

- **API Örnekleri:** [`docs/api_examples.md`](docs/api_examples.md) - API kullanım örnekleri
- **Monitoring & Logging:** [`docs/monitoring/LOGGING_GUIDE.md`](docs/monitoring/LOGGING_GUIDE.md) - Logging rehberi
- **Proje Yönetimi:** [`todo/`](todo/) - Todo sistemi ve proje yönetimi dosyaları

---

## 🔗 İletişim Protokolü

**Detaylı protokol bilgileri için:** [API Referansı](docs/api_reference.md#esp32-hex-komut-protokolü) dosyasına bakınız.

**Özet:**
- ESP32-RPi iletişimi: Binary Hex Protokolü (`41 [KOMUT] 2C [DEĞER] 10`, 5 byte)
- Baudrate: 115200
- Detaylı komut listesi ve protokol yapısı için API Referansı'na bakınız

---

## 🚨 Kritik Kurallar

**Tüm kurallar için:** [`.cursorrules`](.cursorrules) dosyasına bakınız.

**Özet:**
- Tüm dosya isimleri İngilizce olmalı
- Virtual environment (env) kullanılmalı
- Test zamanlaması kurallarına uyulmalı (her dosya editinden sonra tüm test suite'i çalıştırılmaz)
- Git commit/push sürekli yapılmalı
- Dokümantasyon güncel tutulmalı

---

## 📝 Lisans

Bu proje özel bir projedir.

---

**Son Güncelleme:** 2025-12-12 05:55:00

