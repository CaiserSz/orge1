# Workspace Otomasyon Standartları

**Oluşturulma Tarihi:** 2025-12-10 02:30:00
**Son Güncelleme:** 2025-12-10 02:30:00
**Version:** 1.0.0
**Durum:** ✅ Aktif

---

## 🎯 Amaç

Workspace standartlarının otomatik kontrol ve güncellemesi için standartlar ve kurallar.

---

## 🔄 Otomatik Kontrol Mekanizması

### 1. Pre-commit Hook Kontrolü

**Dosya:** `.git/hooks/pre-commit`

**Kontrol Edilenler:**
- Kök dizin .md dosyası sayısı (< 30)
- Klasör sayısı (< 20)
- Workspace boyutu (< 100 MB)
- Gereksiz dosyalar (temp, backup, cache)
- Dosya organizasyonu (analiz/audit raporları, standartlar)

**Aksiyon:**
- Uyarı verir ama commit'i engellemez (şimdilik)
- Detaylı rapor için `python3 scripts/workspace_auto_check.py` çalıştırılmalı

### 2. Otomatik Kontrol Script'i

**Dosya:** `scripts/workspace_auto_check.py`

**Kontrol Edilenler:**
- Kök dizin .md dosyası sayısı
- Klasör sayısı
- Workspace boyutu
- Gereksiz dosyalar
- Dosya organizasyonu

**Kullanım:**
```bash
# Sadece kontrol
python3 scripts/workspace_auto_check.py

# Dry-run (değişiklik yapmadan kontrol)
python3 scripts/workspace_auto_check.py --dry-run
```

---

## 📋 AI Agent Kuralları

### Kural 1: Her Dosya Eklendiğinde

**Zorunlu Aksiyonlar:**
1. ✅ Dosya kök dizine mi eklendi? Kontrol et
2. ✅ Analiz/audit raporu mu? → `reports/` klasörüne taşı
3. ✅ Standart dokümantasyon mu? → `docs/standards/` klasörüne taşı
4. ✅ Kök dizin .md dosyası sayısı kontrolü

**Otomatik Kontrol:**
```bash
python3 scripts/workspace_auto_check.py
```

### Kural 2: Her Klasör Oluşturulduğunda

**Zorunlu Aksiyonlar:**
1. ✅ Klasör sayısı kontrolü yap
2. ✅ Standartları aşıyorsa birleştirme veya arşivleme planla

**Otomatik Kontrol:**
```bash
python3 scripts/workspace_auto_check.py
```

### Kural 3: Her Commit Öncesi

**Zorunlu Aksiyonlar:**
1. ✅ Workspace standartları kontrolü
2. ✅ Gereksiz dosyalar kontrolü
3. ✅ Dosya organizasyonu kontrolü

**Otomatik Kontrol:**
- Pre-commit hook otomatik çalışır
- Manuel kontrol: `python3 scripts/workspace_auto_check.py`

---

## 🔍 Kontrol Kriterleri

### Dosya Sayısı Standartları

| Kategori | İdeal | Uyarı Eşiği | Maksimum |
|----------|-------|-------------|----------|
| Kök Dizin .md Dosyaları | < 25 | 25 | 30 |
| Klasör Sayısı | < 15 | 15 | 20 |
| Workspace Boyutu | < 80 MB | 80 MB | 100 MB |

### Dosya Organizasyonu Kuralları

**Kök Dizinde İzin Verilenler:**
- ✅ `README.md` - Ana README
- ✅ `CHANGELOG.md` - Değişiklik geçmişi
- ✅ `CONTRIBUTING.md` - Katkı rehberi
- ✅ `project_info_*.md` - Ana proje bilgileri
- ✅ Yapılandırma dosyaları (`.gitignore`, `pytest.ini`, vb.)

**Kök Dizinde İzin Verilmeyenler:**
- ❌ Analiz/audit raporları → `reports/` klasörüne
- ❌ Standart dokümantasyon → `docs/standards/` klasörüne
- ❌ Geçici dosyalar (`.tmp`, `.bak`, `.old`)
- ❌ Yedek dosyalar (`.backup`, `*_backup.*`)

---

## 🛠️ Otomasyon Geliştirme Planı

### Faz 1: Temel Kontrol (Tamamlandı ✅)
- [x] `workspace_auto_check.py` script'i oluşturuldu
- [x] Pre-commit hook'a kontrol eklendi
- [x] Dosya sayısı kontrolü eklendi
- [x] Klasör sayısı kontrolü eklendi
- [x] Workspace boyutu kontrolü eklendi
- [x] Gereksiz dosya kontrolü eklendi
- [x] Dosya organizasyonu kontrolü eklendi

### Faz 2: Otomatik Düzeltme (Planlanıyor 📋)
- [ ] Otomatik dosya taşıma mekanizması
- [ ] Gereksiz dosyaları otomatik silme
- [ ] Workspace reorganizasyon önerileri

### Faz 3: Proaktif Kontrol (Planlanıyor 📋)
- [ ] CI/CD pipeline'a entegrasyon
- [ ] Haftalık otomatik kontrol
- [ ] Email/notification sistemi

---

## 📝 Kullanım Örnekleri

### Örnek 1: Manuel Kontrol

```bash
# Workspace standartlarını kontrol et
python3 scripts/workspace_auto_check.py

# Çıktı:
# ======================================================================
# WORKSPACE OTOMATIK KONTROL RAPORU
# ======================================================================
# Tarih: 2025-12-10T02:30:00
#
# 📄 Kök Dizin .md Dosyaları: 4 (İdeal: < 25, Limit: 30)
#   ✅ Standartlara uygun
#
# 📁 Klasör Sayısı: 19 (İdeal: < 15, Limit: 20)
#   🟡 Klasör sayısı uyarı eşiğinde: 19 (İdeal: < 15)
#   Aksiyon: Yakında reorganizasyon gerekebilir
```

### Örnek 2: Pre-commit Hook

```bash
# Commit yaparken otomatik kontrol
git commit -m "feat: Yeni özellik"

# Çıktı:
# Running pre-commit checks...
# Checking Python syntax...
# Checking for trailing whitespace...
# Checking todo files consistency...
# Checking workspace standards...
# Workspace standards check found issues.
# Run 'python3 scripts/workspace_auto_check.py' for details.
# Pre-commit checks passed!
```

---

## ⚠️ Önemli Notlar

1. **Otomatik Düzeltme:** Şimdilik sadece kontrol yapılıyor, otomatik düzeltme geliştirilecek
2. **Commit Engelleme:** Pre-commit hook şimdilik sadece uyarı veriyor, commit'i engellemiyor
3. **Manuel Kontrol:** Her önemli değişiklikten sonra manuel kontrol yapılmalı

---

## 🔗 İlgili Dosyalar

- `scripts/workspace_auto_check.py` - Kontrol script'i
- `.git/hooks/pre-commit` - Pre-commit hook
- `docs/standards/WORKSPACE_MANAGEMENT_STANDARDS.md` - Workspace yönetimi standartları
- `docs/standards/TODO_AUTOMATION_STANDARDS.md` - Todo otomasyon standartları

---

**Son Güncelleme:** 2025-12-10 02:30:00

