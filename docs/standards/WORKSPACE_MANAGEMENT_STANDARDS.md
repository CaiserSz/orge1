# Workspace Yönetimi Standartları

**Oluşturulma Tarihi:** 2025-12-09 22:45:00
**Son Güncelleme:** 2025-12-09 22:45:00
**Version:** 1.0.0
**Durum:** ✅ Aktif

---

## 🎯 Amaç

Bu dokümantasyon, workspace yönetimi, dosya organizasyonu, temizlik, arşivleme ve düzen standartlarını belirleyerek:
- Workspace'in anlaşılır ve düzenli kalmasını sağlamak
- Gereksiz dosyaların tespit edilip temizlenmesini sağlamak
- Dosya sayısının kontrol altında tutulmasını sağlamak
- Workspace'in bakımını kolaylaştırmak
- Bilgi kaybını önlemek

için oluşturulmuştur.

---

## 📊 Workspace Metrikleri ve Sınırlamalar

### Dosya Sayısı Sınırlamaları

| Kategori | İdeal | Uyarı Eşiği | Maksimum | Aksiyon |
|----------|-------|-------------|----------|---------|
| **Toplam Dosya** | < 200 | 300 | 400 | Temizlik gerekli |
| **Python Dosyaları** | < 20 | 30 | 40 | Refactor gerekli |
| **Dokümantasyon (.md)** | < 30 | 40 | 50 | Birleştirme/arşivleme |
| **Test Dosyaları** | < 15 | 20 | 25 | Test suite'e böl |
| **Log Dosyaları** | < 10 | 15 | 20 | Eski logları arşivle |
| **Klasör Sayısı** | < 15 | 20 | 25 | Klasör birleştirme |

### Workspace Boyutu Sınırlamaları

| Metrik | İdeal | Uyarı Eşiği | Maksimum |
|--------|-------|-------------|----------|
| **Toplam Boyut** | < 100 MB | 200 MB | 500 MB |
| **env/ Klasörü** | < 50 MB | 100 MB | 200 MB |
| **logs/ Klasörü** | < 10 MB | 20 MB | 50 MB |
| **Dokümantasyon** | < 5 MB | 10 MB | 20 MB |

---

## 🗂️ Workspace Organizasyon Standartları

### Klasör Yapısı Standartları

#### Zorunlu Klasörler
```
/home/basar/charger/
├── api/                    # REST API modülleri
├── esp32/                  # ESP32 iletişim modülleri
├── meter/                  # Meter okuma modülleri
├── tests/                  # Test dosyaları
├── todo/                   # Proje yönetimi
├── logs/                   # Log dosyaları
└── data/                   # Veri dosyaları
```

#### İsteğe Bağlı Klasörler
```
├── ocpp/                   # OCPP implementasyonu
├── scripts/                # Sistem script'leri
├── docs/                   # Ek dokümantasyon (gelecek)
├── archive/                # Arşivlenmiş dosyalar
└── static/                 # Statik dosyalar (HTML, CSS, JS)
```

### Dosya Organizasyonu Kuralları

#### 1. Kök Dizin Dosyaları
**İzin Verilen:**
- ✅ Ana dokümantasyon dosyaları (`README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`)
- ✅ Proje bilgileri (`project_info_*.md`)
- ✅ Standart dokümantasyon (`CODE_DOCUMENTATION_STANDARDS.md`, `BACKUP_ROLLBACK_STANDARDS.md`)
- ✅ Yapılandırma dosyaları (`.gitignore`, `pytest.ini`, `requirements.txt`, `ngrok.yml`)
- ✅ HTML dosyaları (`api_test.html`, `station_form.html`)

**İzin Verilmeyen:**
- ❌ Geçici dosyalar (`.tmp`, `.bak`, `.old`)
- ❌ Yedek dosyalar (`.backup`, `*_backup.*`)
- ❌ Test sonuç dosyaları (kök dizinde)
- ❌ Geliştirme notları (kök dizinde)

#### 2. Klasör İçi Organizasyon
- ✅ Her klasör kendi sorumluluğunda dosyaları içermeli
- ✅ İlgili dosyalar birlikte olmalı
- ✅ Alt klasörler mantıklı şekilde organize edilmeli

---

## 🧹 Workspace Temizlik Standartları

### Gereksiz Dosya Kategorileri

#### 1. Geçici Dosyalar
**Tespit:**
```bash
# Geçici dosyaları bul
find . -name "*.tmp" -o -name "*.temp" -o -name "*.bak" -o -name "*.old"
```

**Aksiyon:**
- ✅ `.gitignore`'a ekle
- ✅ Mevcut dosyaları sil
- ✅ Commit et

#### 2. Yedek Dosyalar
**Tespit:**
```bash
# Yedek dosyaları bul
find . -name "*.backup" -o -name "*_backup.*" -o -name "*_old.*"
```

**Aksiyon:**
- ✅ Refactoring sonrası yedek dosyalar silinmeli
- ✅ Git'te zaten yedek varsa dosya yedeği gereksiz
- ✅ Commit etmeden önce temizle

#### 3. Cache Dosyaları
**Tespit:**
```bash
# Cache dosyalarını bul
find . -name "__pycache__" -o -name "*.pyc" -o -name ".pytest_cache"
```

**Aksiyon:**
- ✅ `.gitignore`'da zaten var
- ✅ Düzenli temizlik yapılmalı
- ✅ Script ile otomatik temizlik

#### 4. Log Dosyaları
**Tespit:**
```bash
# Eski log dosyalarını bul
find logs/ -name "*.log.*" -mtime +30  # 30 günden eski
```

**Aksiyon:**
- ✅ Log rotation aktif (10MB, 5 yedek)
- ✅ Eski loglar arşivlenebilir
- ✅ 30 günden eski loglar silinebilir

#### 5. Kullanılmayan Dosyalar
**Tespit:**
- ✅ Import edilmeyen Python dosyaları
- ✅ Referans edilmeyen dokümantasyon dosyaları
- ✅ Kullanılmayan test dosyaları
- ✅ Eski versiyon dosyaları

**Aksiyon:**
- ✅ Kullanılmıyorsa sil
- ✅ Gelecekte kullanılacaksa arşivle
- ✅ Git history'de zaten var

### Temizlik Checklist

#### Haftalık Temizlik
- [ ] Geçici dosyalar temizlendi mi?
- [ ] Yedek dosyalar temizlendi mi?
- [ ] Cache dosyaları temizlendi mi?
- [ ] Eski log dosyaları kontrol edildi mi?
- [ ] Kullanılmayan dosyalar tespit edildi mi?

#### Aylık Temizlik
- [ ] Workspace metrikleri kontrol edildi mi?
- [ ] Dosya sayısı sınırları kontrol edildi mi?
- [ ] Workspace boyutu kontrol edildi mi?
- [ ] Arşivleme ihtiyacı değerlendirildi mi?
- [ ] `WORKSPACE_INDEX.md` güncellendi mi?

---

## 📦 Arşivleme Standartları

### Arşivleme Kriterleri

#### Ne Zaman Arşivlenmeli?

1. **Eski Dokümantasyon**
   - 6+ ay güncellenmemiş
   - Yerine yeni versiyon var
   - Artık referans edilmiyor

2. **Eski Audit Raporları**
   - Sorunlar çözüldü
   - Yeni audit raporları var
   - Geçmiş referans için tutulmalı

3. **Eski Test Sonuçları**
   - Yeni testler var
   - Geçmiş karşılaştırma için tutulmalı

4. **Eski Versiyon Dosyaları**
   - Yeni versiyon aktif
   - Geçmiş referans için tutulmalı

### Arşivleme Yöntemleri

#### 1. Git Archive (Önerilen)
```bash
# Belirli tarihteki dosyaları arşivle
git archive --format=tar.gz --output=archive/YYYYMMDD.tar.gz HEAD

# Belirli klasörü arşivle
git archive --format=tar.gz --output=archive/docs-YYYYMMDD.tar.gz HEAD:docs/
```

#### 2. Arşiv Klasörü
```
archive/
├── 2025-12/
│   ├── old_docs/
│   ├── old_tests/
│   └── old_reports/
└── README.md  # Arşiv içeriği açıklaması
```

#### 3. Git Tag ile Versiyonlama
```bash
# Eski versiyonu tag'le
git tag -a archive/v1.0.0 -m "Archived version"

# Arşivlenmiş dosyaları sil
git rm <files>
git commit -m "chore: Archive old files"
```

### Arşivleme Checklist

#### Arşivleme Öncesi
- [ ] Dosyalar gerçekten kullanılmıyor mu?
- [ ] Git history'de zaten var mı?
- [ ] Arşiv klasörü oluşturuldu mu?
- [ ] Arşiv içeriği dokümante edildi mi?

#### Arşivleme Sonrası
- [ ] Dosyalar arşiv klasörüne taşındı mı?
- [ ] `WORKSPACE_INDEX.md` güncellendi mi?
- [ ] Git commit yapıldı mı?
- [ ] Arşiv içeriği dokümante edildi mi?

---

## 📋 Workspace Düzen Standartları

### Dosya İsimlendirme Kuralları

#### Dokümantasyon Dosyaları
- ✅ `UPPERCASE_WITH_UNDERSCORES.md` (ana dokümantasyon)
- ✅ `lowercase_with_underscores.md` (alt dokümantasyon)
- ✅ Tarih formatı: `YYYYMMDD` veya `YYYYMMDD_HHMM`
- ✅ Versiyon formatı: `v1.0.0` veya `1.0.0`

**Örnekler:**
- ✅ `PROJECT_INFO_20251208_145614.md`
- ✅ `CODE_DOCUMENTATION_STANDARDS.md`
- ✅ `BACKUP_ROLLBACK_STANDARDS.md`
- ✅ `WORKSPACE_MANAGEMENT_STANDARDS.md`

#### Kod Dosyaları
- ✅ `snake_case.py` (Python)
- ✅ `PascalCase.py` (sınıf dosyaları için)
- ✅ `kebab-case.html` (HTML dosyaları)

### Dosya Organizasyonu Kuralları

#### 1. İlgili Dosyalar Birlikte
- ✅ API dosyaları `api/` klasöründe
- ✅ ESP32 dosyaları `esp32/` klasöründe
- ✅ Test dosyaları `tests/` klasöründe
- ✅ Dokümantasyon kök dizinde veya `docs/` klasöründe

#### 2. Dosya Gruplama
- ✅ Standart dokümantasyonlar birlikte
- ✅ Audit raporları birlikte
- ✅ Test dosyaları birlikte
- ✅ Yapılandırma dosyaları birlikte

### Workspace Index Güncelleme

#### Ne Zaman Güncellenmeli?
- ✅ Yeni dosya eklendiğinde
- ✅ Dosya silindiğinde
- ✅ Dosya taşındığında
- ✅ Klasör yapısı değiştiğinde
- ✅ Aylık düzenli kontrol

#### Güncelleme Formatı
```markdown
#### `dosya_adi.md`
- **Ne:** Dosya açıklaması
- **Amaç:** Dosyanın amacı
- **İçerik:** İçerik özeti
- **Ne Zaman:** Oluşturulma tarihi
- **Versiyon:** Versiyon numarası
- **İlgili Dosyalar:** İlgili dosyalar
```

---

## 🔍 Workspace Kontrol ve İzleme

### Otomatik Kontroller

#### Pre-commit Hook (Gelecek)
```bash
# Workspace metrikleri kontrolü
# Dosya sayısı kontrolü
# Gereksiz dosya kontrolü
# Cache temizliği
```

#### CI/CD Pipeline (Gelecek)
```yaml
# Automated checks:
# - File count limits
# - Workspace size limits
# - Unused file detection
# - Cache cleanup
```

### Manuel Kontroller

#### Her Commit Öncesi
1. ✅ Geçici dosyalar temizlendi mi?
2. ✅ Yedek dosyalar temizlendi mi?
3. ✅ Cache dosyaları temizlendi mi?
4. ✅ `WORKSPACE_INDEX.md` güncellendi mi?

#### Haftalık Kontrol
1. ✅ Workspace metrikleri kontrol et
2. ✅ Dosya sayısı kontrol et
3. ✅ Workspace boyutu kontrol et
4. ✅ Gereksiz dosyaları tespit et
5. ✅ Temizlik yap

#### Aylık Kontrol
1. ✅ Arşivleme ihtiyacı değerlendir
2. ✅ Eski dosyaları arşivle
3. ✅ `WORKSPACE_INDEX.md` güncelle
4. ✅ Workspace organizasyonu gözden geçir

---

## 🎯 Öncelikli Aksiyonlar

### Acil (Maksimum Sınır Aşıldı)

1. **Workspace Dosya Sayısı Kontrolü**
   - 🔴 **Durum:** Mevcut: 3486 dosya (çoğu env/ içinde)
   - **Aksiyon:** `env/` klasörü `.gitignore`'da zaten var
   - **Öncelik:** Düşük (env/ hariç gerçek dosya sayısı kontrol edilmeli)

### Önemli (Uyarı Eşiği Yakın)

2. **Cache Dosyaları Temizliği**
   - 🟡 **Durum:** `__pycache__/` klasörleri mevcut
   - **Aksiyon:** Düzenli temizlik script'i oluştur
   - **Öncelik:** Orta

3. **WORKSPACE_INDEX.md Güncelleme**
   - 🟡 **Durum:** Yeni dosyalar eklenmiş olabilir
   - **Aksiyon:** Yeni dosyaları ekle
   - **Öncelik:** Orta

---

## 🛠️ Temizlik Script'leri

### Cache Temizleme Script'i
```bash
#!/bin/bash
# clean_cache.sh

echo "Cleaning Python cache files..."
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null

echo "Cache cleaned!"
```

### Geçici Dosya Temizleme Script'i
```bash
#!/bin/bash
# clean_temp.sh

echo "Cleaning temporary files..."
find . -type f -name "*.tmp" -delete
find . -type f -name "*.temp" -delete
find . -type f -name "*.bak" -delete
find . -type f -name "*.old" -delete
find . -type f -name "*.backup" -delete

echo "Temporary files cleaned!"
```

### Workspace Metrikleri Script'i
```bash
#!/bin/bash
# workspace_metrics.sh

echo "=== Workspace Metrics ==="
echo ""
echo "Total files: $(find . -type f | wc -l)"
echo "Total directories: $(find . -type d | wc -l)"
echo "Total size: $(du -sh . | cut -f1)"
echo ""
echo "Python files: $(find . -name "*.py" -type f | wc -l)"
echo "Documentation files: $(find . -name "*.md" -type f | wc -l)"
echo "Test files: $(find tests -name "*.py" -type f 2>/dev/null | wc -l)"
echo ""
echo "Cache directories: $(find . -name "__pycache__" -type d | wc -l)"
echo "Temporary files: $(find . -name "*.tmp" -o -name "*.bak" | wc -l)"
```

---

## 📝 Örnek Senaryolar

### Senaryo 1: Yeni Dosya Eklendiğinde

```bash
# 1. Dosyayı oluştur
touch NEW_FEATURE.md

# 2. WORKSPACE_INDEX.md'ye ekle
# - Dosya açıklaması
# - Amaç
# - İçerik
# - Oluşturulma tarihi

# 3. Git commit
git add NEW_FEATURE.md WORKSPACE_INDEX.md
git commit -m "docs: Add new feature documentation"
```

### Senaryo 2: Gereksiz Dosya Tespit Edildiğinde

```bash
# 1. Dosyayı kontrol et
# - Kullanılıyor mu?
# - Referans ediliyor mu?
# - Git history'de var mı?

# 2. Kullanılmıyorsa:
# - Git'te varsa: Sil (git rm)
# - Git'te yoksa: Direkt sil

# 3. WORKSPACE_INDEX.md'den çıkar

# 4. Git commit
git add .
git commit -m "chore: Remove unused file"
```

### Senaryo 3: Workspace Temizliği

```bash
# 1. Cache temizle
./scripts/clean_cache.sh

# 2. Geçici dosyaları temizle
./scripts/clean_temp.sh

# 3. Metrikleri kontrol et
./scripts/workspace_metrics.sh

# 4. WORKSPACE_INDEX.md güncelle

# 5. Git commit
git add .
git commit -m "chore: Workspace cleanup"
```

---

## 🔗 İlgili Dokümantasyon

- `.gitignore` - Git ignore kuralları
- `WORKSPACE_INDEX.md` - Workspace indeksi
- `CODE_DOCUMENTATION_STANDARDS.md` - Kod standartları
- `BACKUP_ROLLBACK_STANDARDS.md` - Yedekleme standartları
- `.cursorrules` - Proje kuralları

---

## 📝 Notlar

- Bu standartlar proje boyunca uygulanacaktır
- Standartlar zamanla güncellenebilir (versiyon kontrolü ile)
- İstisnai durumlar dokümante edilmelidir
- Tüm geliştiriciler bu standartlara uymalıdır

---

**Son Güncelleme:** 2025-12-09 22:45:00

