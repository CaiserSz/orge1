# Standartlar ve Otomasyon Aktarımı - Diğer Proje İçin Prompt

**Oluşturulma Tarihi:** 2025-12-10 03:00:00
**Amaç:** Diğer projeye standartlar ve otomasyon sistemini aktarmak için AI agent'a verilecek prompt

---

## 🎯 Görev: Standartlar ve Otomasyon Sistemi Kurulumu

Merhaba! Şu anda `/home/basar/charger` projesinde başarıyla uygulanan **standartlar ve otomasyon sistemini** bu projeye de kurmak istiyorum.

### 📋 Yapılacaklar

Bu projeye şu sistemleri kurmalısın:

1. **Standart Dokümantasyonları** (`docs/standards/` klasörü)
2. **Otomasyon Script'leri** (`scripts/` klasörü)
3. **`.cursorrules` Güncellemeleri** (standart kuralları ekle)
4. **Pre-commit Hook** (otomatik kontroller)
5. **GitHub Actions CI/CD** (opsiyonel)

---

## 📚 Referans Proje: `/home/basar/charger`

Referans projede şu yapı mevcut:

### 1. Standart Dokümantasyonları

**Konum:** `/home/basar/charger/docs/standards/`

**Dosyalar:**
- `CODE_DOCUMENTATION_STANDARDS.md` - Kod ve dokümantasyon boyut standartları
- `BACKUP_ROLLBACK_STANDARDS.md` - Yedekleme ve geri dönüş standartları
- `WORKSPACE_MANAGEMENT_STANDARDS.md` - Workspace yönetimi standartları
- `TODO_AUTOMATION_STANDARDS.md` - Todo otomasyon standartları
- `AUTOMATION_COMPLETE.md` - Otomasyon sistemi özeti

**İçerik:**
- Dosya boyutu sınırlamaları (satır sayısı, KB)
- Fonksiyon/sınıf/metod standartları
- Workspace metrikleri ve sınırlamaları
- Yedekleme ve geri dönüş prosedürleri
- Todo sistemi otomasyon kuralları

### 2. Otomasyon Script'leri

**Konum:** `/home/basar/charger/scripts/`

**Dosyalar:**
- `todo_auto_check.py` - Todo dosyaları tutarlılık kontrolü
- `todo_auto_update.py` - Todo dosyaları otomatik güncelleme
- `workspace_auto_check.py` - Workspace standartları kontrolü
- `standards_auto_check.py` - Kod/dokümantasyon standartları kontrolü
- `code_quality_auto_check.py` - Kod kalitesi kontrolü (Black, Ruff)

**Fonksiyonlar:**
- Dosya boyutu kontrolü (satır sayısı)
- Standart ihlalleri tespiti
- Otomatik `master_next.md` güncelleme önerileri
- Workspace metrikleri kontrolü
- Gereksiz dosya tespiti

### 3. `.cursorrules` Kuralları

**Konum:** `/home/basar/charger/.cursorrules`

**Eklenen Kurallar:**
- **KRİTİK KURAL: Kod ve Dokümantasyon Boyut Standartları**
- **KRİTİK KURAL: Tespitlerin Todo Sistemine Eklenmesi**
- **KRİTİK KURAL: Yedekleme ve Geri Dönüş Standartları**
- **KRİTİK KURAL: Workspace Yönetimi Standartları**

### 4. Pre-commit Hook

**Konum:** `/home/basar/charger/.git/hooks/pre-commit`

**Kontroller:**
- Python syntax kontrolü
- Trailing whitespace kontrolü
- Large files kontrolü (> 10MB)
- Todo dosyaları tutarlılık kontrolü
- Workspace standartları kontrolü
- Standart kontrol (dosya boyutu)

---

## 🚀 Adım Adım Kurulum Talimatları

### Faz 1: Standart Dokümantasyonlarını Oluştur

1. **`docs/standards/` klasörünü oluştur**
   ```bash
   mkdir -p docs/standards
   ```

2. **Referans projeden standart dosyalarını oku ve bu projeye uyarla**
   - `/home/basar/charger/docs/standards/CODE_DOCUMENTATION_STANDARDS.md`
   - `/home/basar/charger/docs/standards/BACKUP_ROLLBACK_STANDARDS.md`
   - `/home/basar/charger/docs/standards/WORKSPACE_MANAGEMENT_STANDARDS.md`
   - `/home/basar/charger/docs/standards/TODO_AUTOMATION_STANDARDS.md`
   - `/home/basar/charger/docs/standards/AUTOMATION_COMPLETE.md`

3. **Her dosyayı bu projeye uyarla:**
   - Proje adını değiştir
   - Proje kök dizinini değiştir (`/home/basar/charger` → bu projenin kök dizini)
   - Proje-spesifik bilgileri güncelle (klasör yapısı, dosya isimleri vb.)
   - Standartları projenin ihtiyaçlarına göre ayarla (gerekirse)

### Faz 2: Otomasyon Script'lerini Oluştur

1. **`scripts/` klasörünü oluştur** (yoksa)
   ```bash
   mkdir -p scripts
   ```

2. **Referans projeden script'leri oku ve bu projeye uyarla**
   - `/home/basar/charger/scripts/todo_auto_check.py`
   - `/home/basar/charger/scripts/todo_auto_update.py`
   - `/home/basar/charger/scripts/workspace_auto_check.py`
   - `/home/basar/charger/scripts/standards_auto_check.py`
   - `/home/basar/charger/scripts/code_quality_auto_check.py`

3. **Her script'i bu projeye uyarla:**
   - `PROJECT_ROOT` değişkenini bu projenin kök dizinine ayarla
   - Klasör yapısını bu projeye göre güncelle (`api/`, `tests/`, `docs/` vb.)
   - Standartları bu projenin standartlarına göre ayarla
   - Proje-spesifik dosya yollarını güncelle

4. **Script'leri çalıştırılabilir yap**
   ```bash
   chmod +x scripts/*.py
   ```

### Faz 3: `.cursorrules` Dosyasını Güncelle

1. **Mevcut `.cursorrules` dosyasını oku** (varsa)

2. **Referans projeden kritik kuralları ekle:**
   - `/home/basar/charger/.cursorrules` dosyasını oku
   - Şu bölümleri ekle:
     - **KRİTİK KURAL: Kod ve Dokümantasyon Boyut Standartları**
     - **KRİTİK KURAL: Tespitlerin Todo Sistemine Eklenmesi**
     - **KRİTİK KURAL: Yedekleme ve Geri Dönüş Standartları**
     - **KRİTİK KURAL: Workspace Yönetimi Standartları**

3. **Kuralları bu projeye uyarla:**
   - Proje kök dizinini değiştir
   - Proje-spesifik dosya yollarını güncelle
   - Standartları bu projenin ihtiyaçlarına göre ayarla

### Faz 4: Pre-commit Hook Kurulumu

1. **`.git/hooks/pre-commit` dosyasını oluştur veya güncelle**

2. **Referans projeden pre-commit hook'u oku:**
   - `/home/basar/charger/.git/hooks/pre-commit`

3. **Hook'u bu projeye uyarla:**
   - Script yollarını güncelle
   - Proje-spesifik kontrolleri ekle/çıkar

4. **Hook'u çalıştırılabilir yap**
   ```bash
   chmod +x .git/hooks/pre-commit
   ```

### Faz 5: Test ve Doğrulama

1. **Script'leri test et:**
   ```bash
   python3 scripts/todo_auto_check.py
   python3 scripts/workspace_auto_check.py
   python3 scripts/standards_auto_check.py
   python3 scripts/code_quality_auto_check.py
   ```

2. **Pre-commit hook'u test et:**
   ```bash
   git add .
   git commit -m "test: Pre-commit hook test"
   ```

3. **Standartları doğrula:**
   - Standart dokümantasyonların doğru oluşturulduğunu kontrol et
   - Script'lerin çalıştığını kontrol et
   - `.cursorrules` dosyasının güncellendiğini kontrol et

---

## 📝 Önemli Notlar

### Proje-Spesifik Uyarlamalar

1. **Klasör Yapısı:**
   - Referans projede: `api/`, `esp32/`, `meter/`, `tests/`, `todo/`, `logs/`
   - Bu projede hangi klasörler var? Bunları güncelle

2. **Dosya İsimleri:**
   - Referans projede: `api/main.py`, `project_info_*.md`
   - Bu projede hangi ana dosyalar var? Bunları güncelle

3. **Standartlar:**
   - Referans projede: API endpoint max 600 satır, Modül max 500 satır
   - Bu projenin ihtiyaçlarına göre standartları ayarla

4. **Todo Sistemi:**
   - Referans projede: `todo/master_next.md`, `todo/master_done.md`, `todo/master_live.md`
   - Bu projede todo sistemi var mı? Yoksa oluşturmalı mısın?

### Uyarlama Checklist

- [ ] Proje kök dizini güncellendi mi?
- [ ] Klasör yapısı güncellendi mi?
- [ ] Dosya yolları güncellendi mi?
- [ ] Standartlar projeye uygun mu?
- [ ] Script'ler çalışıyor mu?
- [ ] Pre-commit hook çalışıyor mu?
- [ ] `.cursorrules` güncellendi mi?
- [ ] Dokümantasyonlar doğru mu?

---

## 🔍 Referans Dosyaların Tam Yolları

### Standart Dokümantasyonları
```
/home/basar/charger/docs/standards/CODE_DOCUMENTATION_STANDARDS.md
/home/basar/charger/docs/standards/BACKUP_ROLLBACK_STANDARDS.md
/home/basar/charger/docs/standards/WORKSPACE_MANAGEMENT_STANDARDS.md
/home/basar/charger/docs/standards/TODO_AUTOMATION_STANDARDS.md
/home/basar/charger/docs/standards/AUTOMATION_COMPLETE.md
```

### Otomasyon Script'leri
```
/home/basar/charger/scripts/todo_auto_check.py
/home/basar/charger/scripts/todo_auto_update.py
/home/basar/charger/scripts/workspace_auto_check.py
/home/basar/charger/scripts/standards_auto_check.py
/home/basar/charger/scripts/code_quality_auto_check.py
```

### Konfigürasyon Dosyaları
```
/home/basar/charger/.cursorrules
/home/basar/charger/.git/hooks/pre-commit
```

---

## ✅ Başarı Kriterleri

Kurulum başarılı sayılır eğer:

1. ✅ Tüm standart dokümantasyonlar `docs/standards/` klasöründe mevcut
2. ✅ Tüm otomasyon script'leri `scripts/` klasöründe mevcut ve çalışıyor
3. ✅ `.cursorrules` dosyası güncellenmiş ve kritik kurallar eklenmiş
4. ✅ Pre-commit hook kurulmuş ve çalışıyor
5. ✅ Script'ler test edilmiş ve çalışıyor
6. ✅ Standartlar bu projeye uyarlanmış
7. ✅ Tüm dosya yolları ve proje-spesifik bilgiler güncellenmiş

---

## 🎯 Sonuç

Bu prompt'u takip ederek, referans projedeki (`/home/basar/charger`) standartlar ve otomasyon sistemini bu projeye başarıyla aktarabilirsin.

**Önemli:** Her adımda proje-spesifik uyarlamalar yapmayı unutma! Sadece kopyala-yapıştır yapma, projeye özel ayarlamalar yap.

**Başarılar!** 🚀

---

**Oluşturulma Tarihi:** 2025-12-10 03:00:00
**Referans Proje:** `/home/basar/charger`
**Durum:** ✅ Hazır

