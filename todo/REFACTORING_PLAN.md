# Refactoring Planı - Kod ve Dokümantasyon Standartları

**Oluşturulma Tarihi:** 2025-12-09 22:00:00  
**Son Güncelleme:** 2025-12-21 16:55:00  
**Version:** 1.1.0

---

## 🎯 Amaç

Bu dokümantasyon, kod ve dokümantasyon standartlarına uygunluk için yapılması gereken refactoring işlemlerini planlar.

---

## 🔴 Acil Refactoring (Maksimum Sınır Aşıldı)

### 1. `project_info_20251208_145614.md` (1245 satır)

**Durum:** 🔴 Maksimum sınır (1200 satır) aşıldı  
**Öncelik:** Yüksek  
**Tahmini Süre:** 2-3 saat

#### Bölümleme Planı

```
project_info_20251208_145614.md (300 satır)
├── Genel Bilgiler
├── Sistem Mimarisi
├── API Referansı (link)
└── Versiyon Geçmişi

docs/
├── api_reference.md (300 satır)
│   ├── REST API Endpoint'leri
│   ├── ESP32 Protokolü
│   └── API Örnekleri
├── architecture.md (300 satır)
│   ├── Sistem Mimarisi
│   ├── Modül Yapısı
│   └── Veri Akışı
├── deployment.md (200 satır)
│   ├── Kurulum
│   ├── Yapılandırma
│   └── Servis Yönetimi
└── troubleshooting.md (200 satır)
    ├── Sorun Giderme
    ├── Log Analizi
    └── Hata Kodları
```

#### Aksiyon Adımları

1. ✅ `docs/` klasörü oluştur
2. ✅ İçeriği bölümlere ayır
3. ✅ Ana dosyada index ve linkler oluştur
4. ✅ Cross-reference'ları güncelle
5. ✅ Test et ve doğrula

---

### 2. OCPP Modülleri (Phase‑1) — `ocpp/main.py` + `ocpp/handlers.py`

**Durum:** ✅ Tamamlandı (2025-12-21) — OCPP modülleri satır limitlerine indirildi (<=500)  
**Öncelik:** Yüksek (prod-hardening / bakım riski)  
**Son Durum Boyutları (örnek):**
- `ocpp/main.py`: 315 satır
- `ocpp/handlers.py`: 460 satır
- `ocpp/states.py`: 444 satır

#### Kritik Kısıt
Standartlara tam uyum için OCPP klasörü özelinde sınırlı sayıda yeni `.py` modülü (yeni klasör yok) istisnası gerekiyordu. Bu istisna kullanıcı onayıyla uygulanarak Plan B tamamlandı.

#### Plan A (Kural İhlali Olmadan / Kısa Vadeli)
Amaç: Standart ihlalini “bilinen risk” olarak yönetirken sahada arıza/operasyon maliyetini azaltmak.

- ✅ Systemd runbook + env provisioning + `--once` JSON raporu (ops kanıt) tamamlandı (SSOT: `docs/deployment.md`)
- ✅ SIGTERM graceful shutdown eklendi (`ocpp/main.py`, `ocpp/handlers.py`)
- ✅ Tamamlandı: büyük refactor için karar/izin alındı ve uygulandı (Plan B)

#### Plan B (Önerilen / Standartlara Tam Uyum)
Amaç: OCPP kodunu modüler hale getirip dosya limitlerine uymak (bakım kolaylığı + yan etki riskini azaltma).

**Gereken:** OCPP klasörü özelinde sınırlı yeni `.py` modül istisnası (yalnızca `.py`, yeni klasör yok).

Uygulanan bölme (gerçek):

```
ocpp/
├── main.py               (entrypoint: args/env + run)
├── runtime_config.py     (NEW) OcppRuntimeConfig + env/config load
├── handlers.py           (v201 adapter + ws connect loop; StationCP ayrı modülde)
├── v201_station.py       (NEW) v201 StationCP factory (daemon/remote ops)
├── v16_adapter.py        (NEW) OCPP 1.6J adapter (fallback)
├── states.py             (shared helpers, poller, auth, utils)
├── once_report.py        (NEW) --once JSON raporu orchestrator
├── once_v201.py          (NEW) v201 --once evidence runner
└── once_v201_station.py  (NEW) v201 StationCP factory (--once inbound capture)
```

**Aksiyon Adımları (özet):**
1) ✅ Refactor branch: `refactor/ocpp-modularize-phase1`
2) ✅ `ocpp/main.py` içinden config/once/v16 parçaları yeni modüllere taşındı
3) ✅ `ocpp/handlers.py` içindeki StationCP mantığı `ocpp/v201_station.py` modülüne taşındı
4) ✅ `py_compile` + ilgili testler: `tests/test_integration.py` (v201 remote ops + v16 smoke) geçti
5) ✅ Küçük commit’ler + rollback tag: `v2025-12-21-pre-ocpp-modularize`

---

## 🟡 Önemli Refactoring (Uyarı Eşiği Aşıldı)

### 2. `api/main.py` (591 satır)

**Durum:** 🟡 Uyarı eşiği (600 satır) yakın  
**Öncelik:** Orta  
**Tahmini Süre:** 3-4 saat

#### Router'lara Bölme Planı

```
api/
├── main.py (200 satır)
│   ├── FastAPI app setup
│   ├── Middleware
│   └── Global exception handler
├── routers/
│   ├── __init__.py
│   ├── charge.py (150 satır)
│   │   ├── POST /api/charge/start
│   │   └── POST /api/charge/stop
│   ├── status.py (100 satır)
│   │   ├── GET /api/status
│   │   └── GET /api/health
│   ├── current.py (100 satır)
│   │   ├── POST /api/maxcurrent
│   │   └── GET /api/current/available
│   └── test.py (100 satır)
│       ├── GET /test
│       └── GET /api/test/key
└── dependencies.py (50 satır)
    └── Common dependencies
```

#### Aksiyon Adımları

1. ✅ `api/routers/` klasörü oluştur
2. ✅ Endpoint'leri router'lara taşı
3. ✅ `main.py`'yi sadeleştir
4. ✅ Import'ları güncelle
5. ✅ Test et ve doğrula

---

### 3. `MULTI_EXPERT_ANALYSIS.md` (1115 satır)

**Durum:** 🟡 Uyarı eşiği (1000 satır) aşıldı  
**Öncelik:** Orta  
**Tahmini Süre:** 1-2 saat

#### Bölümleme Planı

```
MULTI_EXPERT_ANALYSIS.md (300 satır)
├── Executive Summary
├── Genel Değerlendirme
└── Linkler (diğer bölümlere)

docs/analysis/
├── security_expert.md (200 satır)
├── performance_expert.md (200 satır)
├── architecture_expert.md (200 satır)
├── code_quality_expert.md (200 satır)
├── devops_expert.md (200 satır)
└── testing_expert.md (200 satır)
```

#### Aksiyon Adımları

1. ✅ `docs/analysis/` klasörü oluştur
2. ✅ Her uzman analizini ayrı dosyaya taşı
3. ✅ Ana dosyada özet ve linkler oluştur
4. ✅ Cross-reference'ları güncelle
5. ✅ Test et ve doğrula

---

## 🟢 İsteğe Bağlı Refactoring (İdeal Sınırlar İçinde)

### 4. `meter/read_meter.py` (~496 satır)

**Durum:** 🟡 Uyarı eşiği (500 satır) yakın  
**Öncelik:** Düşük  
**Tahmini Süre:** 2-3 saat

#### Modüllere Bölme Planı

```
meter/
├── read_meter.py (200 satır)
│   ├── ABBMeterReader class (main)
│   └── Public API
├── modbus.py (150 satır)
│   ├── Modbus RTU protocol
│   └── CRC16 calculation
├── registers.py (100 satır)
│   ├── Register addresses
│   └── Data parsing
└── utils.py (50 satır)
    └── Helper functions
```

#### Aksiyon Adımları

1. ✅ Modülleri ayır
2. ✅ Import'ları güncelle
3. ✅ Test et ve doğrula

---

## 📊 Refactoring Öncelikleri

### Hafta 1 (Acil)
1. ✅ `project_info_20251208_145614.md` bölümleme (2-3 saat)

### Hafta 2-3 (Önemli)
2. ✅ `api/main.py` router'lara bölme (3-4 saat)
3. ✅ `MULTI_EXPERT_ANALYSIS.md` bölümleme (1-2 saat)

### Gelecek (İsteğe Bağlı)
4. ✅ `meter/read_meter.py` modüllere bölme (2-3 saat)

---

## ✅ Refactoring Checklist

### Her Refactoring İçin

#### Refactoring Öncesi (Yedekleme)
- [ ] Mevcut durum commit edildi mi?
- [ ] Refactoring branch oluşturuldu mu? (`git checkout -b refactor/description`)
- [ ] Tag oluşturuldu mu? (büyük refactoring için) (`git tag -a v1.x.x-pre-refactor`)
- [ ] Dosya yedeklendi mi? (küçük değişiklikler için) (`cp file.py file.py.backup`)
- [ ] Testler geçiyor mu? (mevcut durum) (`pytest`)
- [ ] Dokümantasyon güncel mi?

#### Refactoring Sırasında
- [ ] Yeni dosya yapısını oluştur
- [ ] İçeriği taşı ve düzenle
- [ ] Import/reference'ları güncelle
- [ ] Her adımda test et (`pytest`)
- [ ] Küçük commit'ler yap (`git commit -m "refactor(scope): ..."`)

#### Refactoring Sonrası
- [ ] Tüm testler geçiyor mu? (`pytest`)
- [ ] Syntax kontrolü yapıldı mı?
- [ ] Standartlara uygunluğu kontrol et (`wc -l`, `du -h`)
- [ ] Dokümantasyonu güncelle
- [ ] Yedek dosyalar temizlendi mi? (`rm *.backup`)
- [ ] Git commit ve push
- [ ] Detaylar: `BACKUP_ROLLBACK_STANDARDS.md` dosyasına bakınız

---

## 📝 Notlar

- Refactoring sırasında fonksiyonellik korunmalıdır
- Her refactoring sonrası test edilmelidir
- Git commit'leri küçük ve anlamlı olmalıdır
- Dokümantasyon güncel tutulmalıdır

---

**Son Güncelleme:** 2025-12-21 16:55:00

