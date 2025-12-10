# Workspace Yeniden Organizasyon Planı

**Tarih:** 2025-12-10 01:50:00
**Durum:** Planlama Aşaması
**Amaç:** Workspace standartlarına uygun düzenleme

---

## 🔍 Mevcut Durum Analizi

### Kök Dizin Durumu

**Markdown Dosyaları:** 33 dosya (İdeal < 30, Uyarı 40)
- ✅ Uyarı eşiğinde ama ideal sınırı aşılmış

**Klasör Sayısı:** 17 klasör (İdeal < 15, Uyarı 20)
- ✅ Uyarı eşiğinde ama ideal sınırı aşılmış

**Toplam Boyut:** 70 MB (İdeal < 100 MB)
- ✅ İdeal sınırlar içinde

### Sorunlar

1. **Kök dizinde çok fazla analiz/audit raporu:**
   - `ANALYSIS_SUMMARY.md`
   - `AUDIT_REPORT_20251209.md`
   - `AUTHORIZATION_LOGIC_REVISED.md`
   - `AUTHORIZATION_WORKAROUND_EXPLAINED.md`
   - `DEEP_DIVE_ANALYSIS_20251210.md`
   - `DEEPDIVE_ANALYSIS_REPORT.md`
   - `DOCUMENTATION_AUDIT.md`
   - `DOCUMENTATION_UPDATE_AUDIT_20251209.md`
   - `ESP32_FIRMWARE_ADVISORY_REPORT.md`
   - `HARDFAULT_END_VERIFICATION.md`
   - `LOGGING_AUDIT.md`
   - `MULTI_EXPERT_ANALYSIS.md`
   - `PRE_LOGGING_AUDIT.md`
   - `PYTHON_SIDE_REVIEW.md`
   - `RPI_ACTION_PLAN.md`
   - `RPI_STRATEGIC_ANALYSIS.md`

2. **Standart dokümantasyon dosyaları kök dizinde:**
   - `BACKUP_ROLLBACK_STANDARDS.md`
   - `CODE_DOCUMENTATION_STANDARDS.md`
   - `WORKSPACE_MANAGEMENT_STANDARDS.md`
   - `WORKSPACE_INDEX.md`

3. **Proje durum raporları kök dizinde:**
   - `PROJECT_STATUS_SUMMARY.md`
   - `NEXT_STEPS_SUMMARY.md`

---

## 📋 Standartlara Göre Hedef Yapı

### Kök Dizin (Sadece Ana Dosyalar)

**Kalacak Dosyalar:**
- `README.md` - Proje ana README
- `CHANGELOG.md` - Değişiklik geçmişi
- `CONTRIBUTING.md` - Katkı rehberi
- `project_info_20251208_145614.md` - Ana proje bilgileri
- `requirements.txt` - Python bağımlılıkları
- `pytest.ini` - Test konfigürasyonu
- `ngrok.yml` - Ngrok konfigürasyonu
- `.cursorrules` - Cursor kuralları

**Taşınacak Dosyalar:**

1. **Analiz ve Audit Raporları** → `reports/` klasörü
   - `ANALYSIS_SUMMARY.md`
   - `AUDIT_REPORT_20251209.md`
   - `AUTHORIZATION_LOGIC_REVISED.md`
   - `AUTHORIZATION_WORKAROUND_EXPLAINED.md`
   - `DEEP_DIVE_ANALYSIS_20251210.md`
   - `DEEPDIVE_ANALYSIS_REPORT.md`
   - `DOCUMENTATION_AUDIT.md`
   - `DOCUMENTATION_UPDATE_AUDIT_20251209.md`
   - `ESP32_FIRMWARE_ADVISORY_REPORT.md`
   - `HARDFAULT_END_VERIFICATION.md`
   - `LOGGING_AUDIT.md`
   - `MULTI_EXPERT_ANALYSIS.md`
   - `PRE_LOGGING_AUDIT.md`
   - `PYTHON_SIDE_REVIEW.md`
   - `RPI_ACTION_PLAN.md`
   - `RPI_STRATEGIC_ANALYSIS.md`

2. **Standart Dokümantasyon** → `docs/standards/` klasörü
   - `BACKUP_ROLLBACK_STANDARDS.md`
   - `CODE_DOCUMENTATION_STANDARDS.md`
   - `WORKSPACE_MANAGEMENT_STANDARDS.md`

3. **Proje Durum Raporları** → `reports/` klasörü
   - `PROJECT_STATUS_SUMMARY.md`
   - `NEXT_STEPS_SUMMARY.md`

4. **Diğer Dokümantasyon** → `docs/` klasörü
   - `API_EXAMPLES.md` → `docs/api_examples.md`
   - `DOCUMENTATION.md` → `docs/README.md` (veya silinebilir)
   - `METER_SETUP.md` → `docs/meter_setup.md`
   - `WIFI_TROUBLESHOOTING.md` → `docs/wifi_troubleshooting.md`
   - `GIT_GITHUB_IMPROVEMENT_PLAN.md` → `docs/git_github_improvement_plan.md`

5. **Workspace İndeksi** → `docs/` klasörü
   - `WORKSPACE_INDEX.md` → `docs/workspace_index.md`

---

## 📁 Yeni Klasör Yapısı

```
/home/basar/charger/
├── README.md                          # Ana README
├── CHANGELOG.md                       # Değişiklik geçmişi
├── CONTRIBUTING.md                    # Katkı rehberi
├── project_info_20251208_145614.md   # Ana proje bilgileri
├── requirements.txt                   # Python bağımlılıkları
├── pytest.ini                        # Test konfigürasyonu
├── ngrok.yml                         # Ngrok konfigürasyonu
├── .cursorrules                      # Cursor kuralları
│
├── api/                              # API modülü
├── esp32/                            # ESP32 modülü
├── meter/                            # Meter modülü
├── ocpp/                             # OCPP modülü
├── tests/                            # Test dosyaları
├── scripts/                          # Script'ler
├── data/                             # Veri dosyaları
├── logs/                             # Log dosyaları
├── logo/                             # Logo dosyaları
│
├── docs/                             # Dokümantasyon
│   ├── api_reference.md
│   ├── architecture.md
│   ├── deployment.md
│   ├── troubleshooting.md
│   ├── api_examples.md               # Taşınacak
│   ├── meter_setup.md                # Taşınacak
│   ├── wifi_troubleshooting.md       # Taşınacak
│   ├── git_github_improvement_plan.md # Taşınacak
│   ├── workspace_index.md            # Taşınacak
│   └── standards/                    # YENİ KLASÖR
│       ├── BACKUP_ROLLBACK_STANDARDS.md
│       ├── CODE_DOCUMENTATION_STANDARDS.md
│       └── WORKSPACE_MANAGEMENT_STANDARDS.md
│
├── reports/                          # YENİ KLASÖR - Analiz ve Audit Raporları
│   ├── ANALYSIS_SUMMARY.md
│   ├── AUDIT_REPORT_20251209.md
│   ├── AUTHORIZATION_LOGIC_REVISED.md
│   ├── AUTHORIZATION_WORKAROUND_EXPLAINED.md
│   ├── DEEP_DIVE_ANALYSIS_20251210.md
│   ├── DEEPDIVE_ANALYSIS_REPORT.md
│   ├── DOCUMENTATION_AUDIT.md
│   ├── DOCUMENTATION_UPDATE_AUDIT_20251209.md
│   ├── ESP32_FIRMWARE_ADVISORY_REPORT.md
│   ├── HARDFAULT_END_VERIFICATION.md
│   ├── LOGGING_AUDIT.md
│   ├── MULTI_EXPERT_ANALYSIS.md
│   ├── PRE_LOGGING_AUDIT.md
│   ├── PYTHON_SIDE_REVIEW.md
│   ├── RPI_ACTION_PLAN.md
│   ├── RPI_STRATEGIC_ANALYSIS.md
│   ├── PROJECT_STATUS_SUMMARY.md
│   └── NEXT_STEPS_SUMMARY.md
│
└── todo/                             # Proje yönetimi
    ├── START_HERE.md
    ├── checkpoint.md
    ├── project_state.md
    ├── master_live.md
    ├── master_next.md
    ├── master_done.md
    └── ...
```

---

## 🎯 Uygulama Planı

### Faz 1: Klasör Oluşturma

1. ✅ `reports/` klasörü oluştur
2. ✅ `docs/standards/` klasörü oluştur

### Faz 2: Dosya Taşıma

1. ✅ Analiz ve audit raporlarını `reports/` klasörüne taşı
2. ✅ Standart dokümantasyonu `docs/standards/` klasörüne taşı
3. ✅ Diğer dokümantasyonu `docs/` klasörüne taşı

### Faz 3: Referans Güncelleme

1. ✅ `project_info_20251208_145614.md` içindeki linkleri güncelle
2. ✅ `.cursorrules` içindeki referansları güncelle
3. ✅ `WORKSPACE_INDEX.md` güncelle
4. ✅ `README.md` güncelle (varsa)

### Faz 4: Doğrulama

1. ✅ Tüm linkler çalışıyor mu?
2. ✅ Dosya sayısı standartlara uygun mu?
3. ✅ Klasör sayısı standartlara uygun mu?
4. ✅ Git commit ve push

---

## 📊 Beklenen Sonuçlar

### Kök Dizin

**Önce:** 33 .md dosyası
**Sonra:** ~8 .md dosyası (README, CHANGELOG, CONTRIBUTING, project_info, vb.)

**İyileştirme:** ✅ İdeal sınırlar içinde (< 30)

### Klasör Sayısı

**Önce:** 17 klasör
**Sonra:** 18 klasör (+1 reports/, +1 docs/standards/)

**İyileştirme:** ✅ Uyarı eşiği içinde (< 20)

### Organizasyon

**Önce:** Dağınık yapı
**Sonra:** Standartlara uygun organize yapı

---

## ⚠️ Dikkat Edilmesi Gerekenler

1. **Git Referansları:** Dosya taşıma sonrası Git history korunur
2. **Link Güncellemeleri:** Tüm iç referanslar güncellenmeli
3. **Import Path'leri:** Python import path'leri değişmeyecek (sadece .md dosyaları taşınıyor)
4. **Test Edilebilirlik:** Taşıma sonrası testler çalışmalı

---

## 🎯 Sonuç

Bu reorganizasyon ile:
- ✅ Workspace standartlarına uyum sağlanacak
- ✅ Kök dizin temizlenecek
- ✅ Dosyalar mantıklı klasörlerde organize edilecek
- ✅ Bakım kolaylığı artacak

---

**Plan Tarihi:** 2025-12-10 01:50:00
**Durum:** Planlama tamamlandı, uygulama bekliyor

